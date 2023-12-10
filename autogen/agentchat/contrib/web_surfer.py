import json
import copy
import logging
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Union, Callable, Literal, Tuple
from autogen import Agent, ConversableAgent, AssistantAgent, UserProxyAgent, GroupChatManager, GroupChat, OpenAIWrapper
from autogen.browser_utils import SimpleTextBrowser
from autogen.code_utils import content_str
from datetime import datetime
from autogen.token_count_utils import count_token, get_max_token_limit

logger = logging.getLogger(__name__)


class WebSurferAgent(ConversableAgent):
    """(In preview) An agent that acts as a basic web surfer that can search the web and visit web pages."""

    DEFAULT_PROMPT = (
        "You are a helpful AI assistant with access to a web browser (via the provided functions). In fact, YOU ARE THE ONLY MEMBER OF YOUR PARTY WITH ACCESS TO A WEB BROWSER, so please help out where you can by performing web searches, navigating pages, and reporting what you find. Today's date is "
        + datetime.now().date().isoformat()
    )

    DEFAULT_DESCRIPTION = "A helpful assistant with access to a web browser. Ask them to perform web searches, open pages, navigate to Wikipedia, answer questions from pages, and generate summaries, or even perform a semantic 'find-in-page' feature that scrolls to parts of the page that are relevant to a natural language query."

    def __init__(
        self,
        name,
        system_message: Optional[Union[str, List]] = DEFAULT_PROMPT,
        description: Optional[str] = DEFAULT_DESCRIPTION,
        is_termination_msg: Optional[Callable[[Dict], bool]] = None,
        max_consecutive_auto_reply: Optional[int] = None,
        human_input_mode: Optional[str] = "TERMINATE",
        function_map: Optional[Dict[str, Callable]] = None,
        code_execution_config: Optional[Union[Dict, Literal[False]]] = None,
        llm_config: Optional[Union[Dict, Literal[False]]] = None,
        summarizer_llm_config: Optional[Union[Dict, Literal[False]]] = None,
        default_auto_reply: Optional[Union[str, Dict, None]] = "",
        browser_config: Optional[Union[Dict, None]] = None,
    ):
        super().__init__(
            name=name,
            system_message=system_message,
            is_termination_msg=is_termination_msg,
            max_consecutive_auto_reply=max_consecutive_auto_reply,
            human_input_mode=human_input_mode,
            function_map=function_map,
            code_execution_config=code_execution_config,
            llm_config=llm_config,
            default_auto_reply=default_auto_reply,
        )

        # What internal model are we using for summarization?
        if summarizer_llm_config is None:
            self.summarizer_llm_config = copy.deepcopy(llm_config)
            if "config_list" in self.summarizer_llm_config:
                preferred_models = [
                    m
                    for m in self.summarizer_llm_config["config_list"]
                    if m["model"] in ["gpt-3.5-turbo-1106", "gpt-3.5-turbo-16k-0613", "gpt-3.5-turbo-16k"]
                ]
                if len(preferred_models) == 0:
                    logger.warning(
                        "The summarizer did not find the preferred model (gpt-3.5-turbo-16k) in the config list. "
                        "Semantic operations on webpages (summarization or semantic find-in-page) might be costly "
                        "or ineffective."
                    )
                else:
                    self.summarizer_llm_config["config_list"] = preferred_models
        else:
            self.summarizer_llm_config = summarizer_llm_config

        # Create the summarizer client
        self.summarization_client = None
        if self.summarizer_llm_config is not None:
            self.summarization_client = OpenAIWrapper(**self.summarizer_llm_config)

        if browser_config is None:
            self.browser = SimpleTextBrowser()
        else:
            self.browser = SimpleTextBrowser(**browser_config)

        # Set the config to support function calling
        inner_llm_config = copy.deepcopy(llm_config)
        inner_llm_config["functions"] = [
            {
                "name": "informational_web_search",
                "description": "Perform an INFORMATIONAL web search query then return the search results.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The informational web search query to perform.",
                        }
                    },
                },
                "required": ["query"],
            },
            {
                "name": "navigational_web_search",
                "description": "Perform a NAVIGATIONAL web search query then immediately navigate to the top result. Useful, for example, to navigate to a particular Wikipedia article or other known destination. Equivalent to Google's \"I'm Feeling Lucky\" button.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The navigational web search query to perform.",
                        }
                    },
                },
                "required": ["query"],
            },
            {
                "name": "visit_page",
                "description": "Visit a webpage at a given URL and return its text.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "The relative or absolute url of the webapge to visit.",
                        }
                    },
                },
                "required": ["url"],
            },
            {
                "name": "page_up",
                "description": "Scroll the viewport UP one page-length in the current webpage and return the new viewport content.",
                "parameters": {"type": "object", "properties": {}},
                "required": [],
            },
            {
                "name": "page_down",
                "description": "Scroll the viewport DOWN one page-length in the current webpage and return the new viewport content.",
                "parameters": {"type": "object", "properties": {}},
                "required": [],
            },
        ]

        # Enable semantic search
        if self.summarization_client is not None:
            inner_llm_config["functions"].append(
                {
                    "name": "answer_from_page",
                    "description": "Uses AI to read the page and directly answer a given question based on the content.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "question": {
                                "type": "string",
                                "description": "The question to directly answer.",
                            },
                            "url": {
                                "type": "string",
                                "description": "[Optional] The url of the page. (Defaults to the current page)",
                            },
                        },
                    },
                    "required": ["question"],
                }
            )
            inner_llm_config["functions"].append(
                {
                    "name": "summarize_page",
                    "description": "Uses AI to summarize the content found at a given url. If the url is not provided, the current page is summarized.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "url": {
                                "type": "string",
                                "description": "[Optional] The url of the page to summarize. (Defaults to current page)",
                            },
                        },
                    },
                    "required": [],
                }
            )
            inner_llm_config["functions"].append(
                {
                    "name": "find_in_page",
                    "description": "Scroll to the part of the page most relevant to a question or query. I.e., an AI-enhanced version of Ctrl+F",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The query to search for, or the question to answer.",
                            },
                            "url": {
                                "type": "string",
                                "description": "[Optional] The url of the page on which to perform a semantic search. (Defaults to current page)",
                            },
                        },
                    },
                    "required": ["query"],
                }
            )
        else:  # Rely on old-school methods
            inner_llm_config["functions"].append(
                {
                    "name": "find_on_page",
                    "description": "Find a string on a the current webpage, and scroll to its position (equivalent to Ctrl+F).",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "find_string": {
                                "type": "string",
                                "description": "The string to find on the page.",
                            }
                        },
                    },
                    "required": ["url"],
                }
            )
            inner_llm_config["functions"].append(
                {
                    "name": "find_next_on_page",
                    "description": "Find the next occurrence of a string on a the current webpage, and scroll to its position.",
                    "parameters": {"type": "object", "properties": {}},
                    "required": [],
                }
            )

        # Set up the inner monologue
        self._assistant = AssistantAgent(
            self.name + "_inner_assistant",
            system_message=system_message,
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

        # Helper fuctions
        def _browser_state():
            header = f"Address: {self.browser.address}\n"
            if self.browser.page_title is not None:
                header += f"Title: {self.browser.page_title}\n"

            start_idx = self.browser._viewport_start_position()
            end_idx = self.browser._viewport_end_position()
            content_length = len(self.browser.page_content)

            header += (
                f"Viewport position: Showing characters {start_idx} - {end_idx} of {content_length} total characters.\n"
            )
            return (header, self.browser.viewport)

        def _informational_search(query):
            self.browser.visit_page(f"bing: {query}")
            header, content = _browser_state()
            return header.strip() + "\n=======================\n" + content

        def _navigational_search(query):
            self.browser.visit_page(f"bing: {query}")

            # Extract the first linl
            m = re.search(r"\[.*?\]\((http.*?)\)", self.browser.page_content)
            if m:
                self.browser.visit_page(m.group(1))

            # Return where we ended up
            header, content = _browser_state()
            return header.strip() + "\n=======================\n" + content

        def _visit_page(url):
            self.browser.visit_page(url)
            header, content = _browser_state()
            return header.strip() + "\n=======================\n" + content

        def _page_up():
            self.browser.page_up()
            header, content = _browser_state()
            return header.strip() + "\n=======================\n" + content

        def _page_down():
            self.browser.page_down()
            header, content = _browser_state()
            return header.strip() + "\n=======================\n" + content

        def _find_on_page(find_string):
            found = self.browser.find_on_page(find_string)
            header, content = _browser_state()
            if not found:
                return (
                    header.strip()
                    + "\n"
                    + f"The string '{self.browser.find_string}' was not found on the page.\n=======================\n"
                    + content
                )
            else:
                return (
                    header.strip()
                    + "\n"
                    + f"Scrolled to result {self.browser.find_idx+1} of {len(self.browser.find_matches)} for string '{self.browser.find_string}'\n=======================\n"
                    + content
                )

        def _find_next_on_page():
            found = self.browser.find_next_on_page()
            header, content = _browser_state()
            if not found:
                return (
                    header.strip()
                    + "\n"
                    + f"The string '{self.browser.find_string}' was not found on the page.\n=======================\n"
                    + content
                )
            else:
                return (
                    header.strip()
                    + "\n"
                    + f"Scrolled to result {self.browser.find_idx+1} of {len(self.browser.find_matches)} for string '{self.browser.find_string}'\n=======================\n"
                    + content
                )

        def _summarize_page(question, url):
            if url is not None and url != self.browser.address:
                self.browser.visit_page(url)

            # We are likely going to need to fix this later, but summarize only as many tokens that fit in the buffer
            limit = 4096
            try:
                limit = get_max_token_limit(self.summarizer_llm_config["config_list"][0]["model"])
            except ValueError:
                pass  # limit is unknown

            if limit < 16000:
                logger.warning(
                    f"The token limit ({limit}) of the WebSurferAgent.summarizer_llm_config, is below the recommended 16k."
                )

            buffer = ""
            for line in re.split(r"([\r\n]+)", self.browser.page_content):
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

            response = self.summarization_client.create(context=None, messages=messages)
            extracted_response = self.summarization_client.extract_text_or_completion_object(response)[0]
            if not isinstance(extracted_response, str):
                return str(extracted_response.model_dump(mode="dict"))  # Not sure what to do here
            else:
                return extracted_response

        def _semantic_find_on_page(query, url):
            if url is not None and url != self.browser.address:
                self.browser.visit_page(url)

            # We are likely going to need to fix this later, but summarize only as many tokens that fit in the buffer
            limit = 4096
            try:
                limit = get_max_token_limit(self.summarizer_llm_config["config_list"][0]["model"])
            except ValueError:
                pass  # limit is unknown

            if limit < 16000:
                logger.warning(
                    f"The token limit ({limit}) of the WebSurferAgent.summarizer_llm_config, is below the recommended 16k."
                )

            lines = list()
            buffer = ""
            line_number = 0
            for line in re.split(r"[\r\n]", self.browser.page_content):
                line_number += 1
                line_indicator = f"[Line {line_number}] "
                line = line + "\n"

                tokens = count_token(buffer + line_indicator + line)
                if tokens + 1024 > limit:  # Leave room for our summary
                    break

                lines.append(line)
                buffer += line_indicator + line

            buffer = buffer.strip()
            if len(buffer) == 0:
                return "Nothing to summarize."

            messages = [
                {
                    "role": "system",
                    "content": "You are a helpful assistant that can find relevant passages in long documents to answer questions.",
                },
                {
                    "role": "user",
                    "content": f"Consider the following document, which contains line number markings:\n\n{buffer}",
                },
                {
                    "role": "user",
                    "content": f"""Read the above document, and think about the answer to the question '{query}'. With this in mind, complete the following:

The answer to the question or query is:
The most relevant direct quote from the page is:
This quote can be found on or near Line:""",
                },
            ]
            # print(json.dumps(messages, indent=4))

            response = self.summarization_client.create(context=None, messages=messages)
            extracted_response = self.summarization_client.extract_text_or_completion_object(response)[0]
            if not isinstance(extracted_response, str):
                return str(extracted_response.model_dump(mode="dict"))  # Not sure what to do here

            m = re.search(r"[Ll]ine\:?\s+(\d+)", extracted_response)
            if m:
                found_line = int(m.group(1))
                return _find_on_page(lines[found_line - 1])
            else:
                return extracted_response

        self._user_proxy.register_function(
            function_map={
                "informational_web_search": lambda query: _informational_search(query),
                "navigational_web_search": lambda query: _navigational_search(query),
                "visit_page": lambda url: _visit_page(url),
                "page_up": lambda: _page_up(),
                "page_down": lambda: _page_down(),
                "find_on_page": lambda find_string: _find_on_page(find_string),
                "find_next_on_page": lambda: _find_next_on_page(),
                "answer_from_page": lambda question=None, url=None: _summarize_page(question, url),
                "summarize_page": lambda question=None, url=None: _summarize_page(None, url),
                "find_in_page": lambda query=None, url=None: _semantic_find_on_page(query, url),
            }
        )

        self.register_reply([Agent, None], WebSurferAgent.generate_surfer_reply)
        self.register_reply([Agent, None], ConversableAgent.generate_code_execution_reply)
        self.register_reply([Agent, None], ConversableAgent.generate_function_call_reply)
        self.register_reply([Agent, None], ConversableAgent.check_termination_and_human_reply)

    def generate_surfer_reply(
        self,
        messages: Optional[List[Dict]] = None,
        sender: Optional[Agent] = None,
        config: Optional[OpenAIWrapper] = None,
    ) -> Tuple[bool, Union[str, Dict, None]]:
        """Generate a reply using autogen.oai."""
        if messages is None:
            messages = self._oai_messages[sender]

        self._user_proxy.reset()
        self._assistant.reset()

        # Clone the messages to give context
        self._assistant.chat_messages[self._user_proxy] = list()
        history = messages[0 : len(messages) - 1]
        for message in history:
            self._assistant.chat_messages[self._user_proxy].append(message)

        # Remind the agent where it is
        self._user_proxy.send(
            f"Your browser is currently open to the page '{self.browser.page_title}' at the address '{self.browser.address}'.",
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
            return True, None if proxy_reply is None else proxy_reply["content"]
