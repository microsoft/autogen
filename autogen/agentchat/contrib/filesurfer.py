import copy
import re
import time
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Union, Callable, Literal, Tuple
from typing_extensions import Annotated

from ... import Agent, ConversableAgent, AssistantAgent, UserProxyAgent, OpenAIWrapper
from ...browser_utils import AbstractMarkdownBrowser, RequestsMarkdownBrowser
from ...token_count_utils import count_token, get_max_token_limit
from ...oai.openai_utils import filter_config


logger = logging.getLogger(__name__)


class FileSurferAgent(ConversableAgent):
    """(In preview) An agent that acts as a basic file surfer that can navigate
    various files. It can open local files, download files, scroll up or down in
    the viewport, find specific words or phrases on the page (ctrl+f), and
    even read the page and answer questions.
    """

    DEFAULT_PROMPT = (
        """You are an AI assistant that can handle tasks that involve files (pdfs,
ppts, txts, images, etc) .

When given a task, first reflect on the goal and if its already accomplished.
If its accomplished already, reply with "TERMINATE".
If not, proceed with the following routine:

    When a task requires interacting with files,
    - check if the chat history contains necessary information
    - if it doesn't, navigate to the correct file and its content
    - once relevant information is available, se the information to complete the task.
    - when task is finished promptly reply with "TERMINATE"

To navigate files use available functions.

YOU ARE THE ONLY MEMBER OF YOUR PARTY WITH ACCESS TO THIS ABILITY,
so help where you can by opening files, navigating pages in the files, and
reporting what you find.

Today's date is """
        + datetime.now().date().isoformat()
    )

    DEFAULT_DESCRIPTION = """A helpful assistant with access to ability to navigate
files. Ask them to open files (local or on the web), download files, etc.
Once on a desired page, ask them to answer questions by
reading the page, generate summaries, find specific words or phrases on the
page (ctrl+f), or even just scroll up or down in the viewport."""

    def __init__(
        self,
        name: str,
        system_message: Optional[Union[str, List[str]]] = DEFAULT_PROMPT,
        description: Optional[str] = DEFAULT_DESCRIPTION,
        is_termination_msg: Optional[Callable[[Dict[str, Any]], bool]] = None,
        max_consecutive_auto_reply: Optional[int] = None,
        llm_config: Optional[Union[Dict, Literal[False]]] = None,
        default_auto_reply: Optional[Union[str, Dict, None]] = "",
        browser: Optional[Union[AbstractMarkdownBrowser, None]] = None,
    ):
        super().__init__(
            name=name,
            system_message=system_message,
            description=description,
            is_termination_msg=is_termination_msg,
            max_consecutive_auto_reply=max_consecutive_auto_reply,
            human_input_mode="NEVER",
            function_map=None,
            code_execution_config=False,
            llm_config=llm_config,
            default_auto_reply=default_auto_reply,
        )

        self.llm_config = copy.deepcopy(llm_config)

        self._summarization_client = OpenAIWrapper(**llm_config)
        self._browser = browser or RequestsMarkdownBrowser(viewport_size=1024 * 5, downloads_folder="coding")
        self._setup_agents()
        self.register_reply([Agent, None], FileSurferAgent.generate_surfer_reply, remove_other_reply_funcs=True)

    def _setup_agents(self) -> None:

        self._assistant = AssistantAgent(
            self.name + "_inner_assistant",
            system_message=self.system_message,  # type: ignore[arg-type]
            llm_config=self.llm_config,
            is_termination_msg=lambda m: False,
        )
        self._user_proxy = UserProxyAgent(
            self.name + "_inner_user_proxy",
            human_input_mode="NEVER",
            code_execution_config=False,
            default_auto_reply="",
            is_termination_msg=lambda m: False,
        )
        self._register_functions()

    def _register_functions(self) -> None:
        """Register the functions for the inner assistant and user proxy."""

        # Helper functions
        def _browser_state() -> Tuple[str, str]:
            header = f"Address: {self._browser.address}\n"
            if self._browser.page_title is not None:
                header += f"Title: {self._browser.page_title}\n"

            current_page = self._browser.viewport_current_page
            total_pages = len(self._browser.viewport_pages)

            address = self._browser.address
            for i in range(len(self._browser.history) - 2, -1, -1):  # Start from the second last
                if self._browser.history[i][0] == address:
                    header += f"You previously visited this page {round(time.time() - self._browser.history[i][1])} seconds ago.\n"
                    break

            header += f"Viewport position: Showing page {current_page+1} of {total_pages}.\n"

            return (header, self._browser.viewport)

        @self._user_proxy.register_for_execution()
        @self._assistant.register_for_llm(
            name="open_local_file", description="Visit a local file at a path and return its text."
        )
        def _open_local_file(url: Annotated[str, "The relative or absolute path of a local file to visit."]) -> str:
            self._browser.open_local_file(url)
            header, content = _browser_state()
            return header.strip() + "\n=======================\n" + content

        @self._user_proxy.register_for_execution()
        @self._assistant.register_for_llm(
            name="download_file", description="Download a file at a given URL and, if possible, return its text."
        )
        def _download_file(url: Annotated[str, "The relative or absolute url of the file to be downloaded."]) -> str:
            self._browser.visit_page(url)
            header, content = _browser_state()
            return header.strip() + "\n=======================\n" + content

        @self._user_proxy.register_for_execution()
        @self._assistant.register_for_llm(
            name="page_up",
            description="Scroll the viewport UP one page-length in the current webpage and return the new viewport content.",
        )
        def _page_up() -> str:
            self._browser.page_up()
            header, content = _browser_state()
            return header.strip() + "\n=======================\n" + content

        @self._user_proxy.register_for_execution()
        @self._assistant.register_for_llm(
            name="page_down",
            description="Scroll the viewport DOWN one page-length in the current webpage and return the new viewport content.",
        )
        def _page_down() -> str:
            self._browser.page_down()
            header, content = _browser_state()
            return header.strip() + "\n=======================\n" + content

        @self._user_proxy.register_for_execution()
        @self._assistant.register_for_llm(
            name="find_on_page_ctrl_f",
            description="Scroll the viewport to the first occurrence of the search string. This is equivalent to Ctrl+F.",
        )
        def _find_on_page_ctrl_f(
            search_string: Annotated[
                str, "The string to search for on the page. This search string supports wildcards like '*'"
            ]
        ) -> str:
            find_result = self._browser.find_on_page(search_string)
            header, content = _browser_state()

            if find_result is None:
                return (
                    header.strip()
                    + "\n=======================\nThe search string '"
                    + search_string
                    + "' was not found on this page."
                )
            else:
                return header.strip() + "\n=======================\n" + content

        @self._user_proxy.register_for_execution()
        @self._assistant.register_for_llm(
            name="find_next",
            description="Scroll the viewport to next occurrence of the search string.",
        )
        def _find_next() -> str:
            find_result = self._browser.find_next()
            header, content = _browser_state()

            if find_result is None:
                return header.strip() + "\n=======================\nThe search string was not found on this page."
            else:
                return header.strip() + "\n=======================\n" + content

        if self._summarization_client is not None:

            @self._user_proxy.register_for_execution()
            @self._assistant.register_for_llm(
                name="read_page_and_answer",
                description="Uses AI to read the page and directly answer a given question based on the content.",
            )
            def _read_page_and_answer(
                question: Annotated[Optional[str], "The question to directly answer."],
                url: Annotated[Optional[str], "[Optional] The url of the page. (Defaults to the current page)"] = None,
            ) -> str:
                if url is not None and url != self._browser.address:
                    self._browser.visit_page(url)

                # We are likely going to need to fix this later, but summarize only as many tokens that fit in the buffer
                limit = 4096
                try:
                    limit = get_max_token_limit(self.llm_config["config_list"][0]["model"])  # type: ignore[index]
                except ValueError:
                    pass  # limit is unknown
                except TypeError:
                    pass  # limit is unknown

                if limit < 16000:
                    logger.warning(
                        f"The token limit ({limit}) of the WebSurferAgent.summarizer_llm_config, is below the recommended 16k."
                    )

                buffer = ""
                for line in re.split(r"([\r\n]+)", self._browser.page_content):
                    tokens = count_token(buffer + line)
                    if tokens + 1024 > limit:  # Leave room for our summary
                        break
                    buffer += line

                buffer = buffer.strip()
                if len(buffer) == 0:
                    return "Nothing to summarize."

                messages = [
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that can summarize long documents to answer question.",
                    }
                ]

                prompt = f"Please summarize the following into one or two paragraph:\n\n{buffer}"
                if question is not None:
                    prompt = f"Please summarize the following into one or two paragraphs with respect to '{question}':\n\n{buffer}"

                messages.append(
                    {"role": "user", "content": prompt},
                )

                response = self._summarization_client.create(context=None, messages=messages)  # type: ignore[union-attr]
                extracted_response = self._summarization_client.extract_text_or_completion_object(response)[0]  # type: ignore[union-attr]
                return str(extracted_response)

            @self._user_proxy.register_for_execution()
            @self._assistant.register_for_llm(
                name="summarize_page",
                description="Uses AI to summarize the content found at a given url. If the url is not provided, the current page is summarized.",
            )
            def _summarize_page(
                url: Annotated[
                    Optional[str], "[Optional] The url of the page to summarize. (Defaults to current page)"
                ] = None
            ) -> str:
                return _read_page_and_answer(url=url, question=None)

    def generate_surfer_reply(
        self,
        messages: Optional[List[Dict[str, str]]] = None,
        sender: Optional[Agent] = None,
        config: Optional[OpenAIWrapper] = None,
    ) -> Tuple[bool, Optional[Union[str, Dict[str, str]]]]:
        """Generate a reply using autogen.oai."""
        if messages is None:
            messages = self._oai_messages[sender]

        self._user_proxy.reset()  # type: ignore[no-untyped-call]
        self._assistant.reset()  # type: ignore[no-untyped-call]

        # Clone the messages to give context
        self._assistant.chat_messages[self._user_proxy] = list()
        history = messages[0 : len(messages) - 1]
        for message in history:
            self._assistant.chat_messages[self._user_proxy].append(message)

        # Remind the agent where it is
        self._user_proxy.send(
            f"Your browser is currently open to the page '{self._browser.page_title}' at the address '{self._browser.address}'.",
            self._assistant,
            request_reply=False,
            silent=True,
        )

        self._user_proxy.send(messages[-1]["content"], self._assistant, request_reply=True, silent=True)
        agent_reply = self._user_proxy.chat_messages[self._assistant][-1]
        proxy_reply = self._user_proxy.generate_reply(
            messages=self._user_proxy.chat_messages[self._assistant], sender=self._assistant
        )

        if proxy_reply == "":  # Was the default reply
            return True, None if agent_reply is None else agent_reply["content"]
        else:
            return True, None if proxy_reply is None else proxy_reply["content"]  # type: ignore[index]
