import json
import copy
import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union, Callable, Literal, Tuple
from typing_extensions import Annotated
from . import Agent, ConversableAgent, AssistantAgent, UserProxyAgent, GroupChatManager, GroupChat, OpenAIWrapper
from .agentchat.contrib.functions.file_utils import LocalFileBrowser
from .code_utils import content_str
from datetime import datetime
from .token_count_utils import count_token, get_max_token_limit
from .oai.openai_utils import filter_config
import mimetypes

logger = logging.getLogger(__name__)


class FileBrowserAgent(ConversableAgent):
    """(In preview) An agent that acts as a basic local file browser that can search and visit local files."""

    DEFAULT_PROMPT = (
        "You are a helpful AI assistant with access to a local file system (via the provided functions). In fact, YOU ARE THE ONLY MEMBER OF YOUR PARTY WITH ACCESS TO A LOCAL FILE SYSTEM, so please help out where you can by performing file searches, navigating files, and reporting what you find. Today's date is "
        + datetime.now().date().isoformat()
    )

    DEFAULT_DESCRIPTION = "A helpful assistant with access to a local file system. Ask them to perform local file searches, open files, navigate to files, answer questions from the file, and or generate summaries."

    def __init__(
        self,
        name: str,
        system_message: Optional[Union[str, List[str]]] = DEFAULT_PROMPT,
        description: Optional[str] = DEFAULT_DESCRIPTION,
        is_termination_msg: Optional[Callable[[Dict[str, Any]], bool]] = None,
        max_consecutive_auto_reply: Optional[int] = None,
        human_input_mode: Optional[str] = "TERMINATE",
        function_map: Optional[Dict[str, Callable]] = None,
        code_execution_config: Union[Dict, Literal[False]] = False,
        llm_config: Optional[Union[Dict, Literal[False]]] = None,
        summarizer_llm_config: Optional[Union[Dict, Literal[False]]] = None,
        default_auto_reply: Optional[Union[str, Dict, None]] = "",
        file_browser_config: Optional[Union[Dict, None]] = None,
    ):
        super().__init__(
            name=name,
            system_message=system_message,
            description=description,
            is_termination_msg=is_termination_msg,
            max_consecutive_auto_reply=max_consecutive_auto_reply,
            human_input_mode=human_input_mode,
            function_map=function_map,
            code_execution_config=code_execution_config,
            llm_config=llm_config,
            default_auto_reply=default_auto_reply,
        )

        self._create_summarizer_client(summarizer_llm_config, llm_config)

        # Create the local file browser
        self.file_browser = LocalFileBrowser(**(file_browser_config if file_browser_config else {}))

        inner_llm_config = copy.deepcopy(llm_config)

        # Set up the inner monologue
        self._assistant = AssistantAgent(
            self.name + "_inner_assistant",
            system_message=system_message,  # type: ignore[arg-type]
            llm_config=inner_llm_config,
            is_termination_msg=lambda m: False,
        )

        self._user_proxy = UserProxyAgent(
            self.name + "_inner_user_proxy",
            human_input_mode="NEVER",
            code_execution_config=False,
            default_auto_reply="",
            is_termination_msg=lambda m: False,
        )

        if inner_llm_config not in [None, False]:
            self._register_functions()

        self._reply_func_list = []
        self.register_reply([Agent, None], FileBrowserAgent.generate_file_browser_reply)
        self.register_reply([Agent, None], ConversableAgent.generate_code_execution_reply)
        self.register_reply([Agent, None], ConversableAgent.generate_function_call_reply)
        self.register_reply([Agent, None], ConversableAgent.check_termination_and_human_reply)

    def _create_summarizer_client(self, summarizer_llm_config: Dict[str, Any], llm_config: Dict[str, Any]) -> None:
        # If the summarizer_llm_config is None, we copy it from the llm_config
        if summarizer_llm_config is None:
            if llm_config is None:  # Nothing to copy
                self.summarizer_llm_config = None
            elif llm_config is False:  # LLMs disabled
                self.summarizer_llm_config = False
            else:  # Create a suitable config
                self.summarizer_llm_config = copy.deepcopy(llm_config)  # type: ignore[assignment]
                if "config_list" in self.summarizer_llm_config:  # type: ignore[operator]
                    preferred_models = filter_config(  # type: ignore[no-untyped-call]
                        self.summarizer_llm_config["config_list"],  # type: ignore[index]
                        {"model": ["gpt-3.5-turbo-1106", "gpt-3.5-turbo-16k-0613", "gpt-3.5-turbo-16k"]},
                    )
                    if len(preferred_models) == 0:
                        logger.warning(
                            "The summarizer did not find the preferred model (gpt-3.5-turbo-16k) in the config list. "
                            "Semantic operations on webpages (summarization or Q&A) might be costly or ineffective."
                        )
                    else:
                        self.summarizer_llm_config["config_list"] = preferred_models  # type: ignore[index]
        else:
            self.summarizer_llm_config = summarizer_llm_config  # type: ignore[assignment]

        # Create the summarizer client
        self.summarization_client = None if self.summarizer_llm_config is False else OpenAIWrapper(**self.summarizer_llm_config)  # type: ignore[arg-type]

    def _register_functions(self) -> None:
        """Register the functions for the inner assistant and user proxy."""

        # Helper functions
        def _file_browser_state() -> Tuple[str, str]:
            header = f"File path: {self.file_browser.current_file}\n"
            # TODO: file_path and file_title?
            # if self.file_browser.file_name is not None:
            #     header += f"File name: {self.file_browser.file_name}\n"

            # TODO: do we need current page and total page for pdf and excel?

            header += "Hint: Looking for something specific on this page? Try calling 'read_page_and_answer'.\n"
            return header #, self.browser.viewport

        @self._user_proxy.register_for_execution()
        @self._assistant.register_for_llm(
            name="visit_file", description="Visit a local file at given path and return its text."
        )
        def _visit_file(file_path: Annotated[str, "The relative or absolute file path to visit."]) -> str:
            self.file_browser.visit_file(file_path)
            # header, content = _file_browser_state()
            header = _file_browser_state()

            return header.strip() + "\n=======================\n" # + content

        if self.summarization_client is not None:

            @self._user_proxy.register_for_execution()
            @self._assistant.register_for_llm(
                name="read_page_and_answer",
                description="Uses AI to read the page and directly answer a given question based on the file content.",
            )
            def _read_page_and_answer(
                question: Annotated[Optional[str], "The question to directly answer."],
                file_path: Annotated[Optional[str], "[Optional] The relative or absolute file path"] = None,
            ) -> str:
                if file_path is not None and file_path != self.file_browser.current_file:
                    self.file_browser.visit_file(file_path)

                # We are likely going to need to fix this later, but summarize only as many tokens that fit in the buffer
                limit = 4096
                try:
                    limit = get_max_token_limit(self.summarizer_llm_config["config_list"][0]["model"])  # type: ignore[index]
                except ValueError:
                    pass  # limit is unknown
                except TypeError:
                    pass  # limit is unknown

                if limit < 16000:
                    logger.warning(
                        f"The token limit ({limit}) of the WebSurferAgent.summarizer_llm_config, is below the recommended 16k."
                    )

                buffer = ""
                for line in re.split(r"([\r\n]+)", self.file_browser.file_content):
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

                response = self.summarization_client.create(context=None, messages=messages)  # type: ignore[union-attr]
                extracted_response = self.summarization_client.extract_text_or_completion_object(response)[0]  # type: ignore[union-attr]
                return str(extracted_response)

            @self._user_proxy.register_for_execution()
            @self._assistant.register_for_llm(
                name="summarize_page",
                description="Uses AI to summarize the content found at the given relative or absolute file path. If the file path is not provided, the current file is summarized.",
            )
            def _summarize_page(
                file_path: Annotated[
                    Optional[str], "[Optional] The relative or absolute file path to summarize."
                ] = None
            ) -> str:
                # TODO: figure out if it's possible to have relative file path
                file_path=self.file_browser.current_file # TODO: file path should NOT be hard coded to current file
                return _read_page_and_answer(file_path=file_path, question=None)

    def generate_file_browser_reply(
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
            f"Your local file browser currently opens '{self.file_browser.file_name}'.",
            self._assistant,
            request_reply=False,
            silent=True,
        )

        self._user_proxy.send(messages[-1]["content"], self._assistant, request_reply=True, silent=True)
        agent_reply = self._user_proxy.chat_messages[self._assistant][-1]
        # print("Agent Reply: " + str(agent_reply))

        proxy_reply = self._user_proxy.generate_reply(
            messages=self._user_proxy.chat_messages[self._assistant], sender=self._assistant
        )
        # print("Proxy Reply: " + str(proxy_reply))

        if proxy_reply == "":  # Was the default reply
            return True, None if agent_reply is None else agent_reply["content"]
        else:
            return True, None if proxy_reply is None else proxy_reply["content"]  # type: ignore[index]
