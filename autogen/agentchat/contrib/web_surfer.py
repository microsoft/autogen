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

    DEFAULT_SURFER_PROMPT = (
        "You are a helpful AI assistant with access to a web browser (via the provided functions). In fact, YOU ARE THE ONLY MEMBER OF YOUR PARTY WITH ACCESS TO A WEB BROWSER, so please help out where you can by performing web searches, navigating pages, and reporting what you find. Today's date is "
        + datetime.now().date().isoformat()
    )

    def __init__(
        self,
        name,
        system_message: Optional[Union[str, List]] = DEFAULT_SURFER_PROMPT,
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
                "name": "bing_search",
                "description": "Perform a search on Bing for a given query, then return the top results.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The Bing web search query to perform.",
                        }
                    },
                },
                "required": ["query"],
            },
            {
                "name": "visit_page",
                "description": "Visit a webpage and return its text.",
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
                "name": "visit_wikipedia",
                "description": "Navigate directly to a wikipedia page on a given topic or title.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "topic_or_title": {
                            "type": "string",
                            "description": "The topic or title of the wikipedia page to visit.",
                        }
                    },
                },
                "required": ["topic_or_title"],
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
                    "name": "summarize_page",
                    "description": "Answer a question or summarize the content found at a given url. If the url is not provided, the current page is summarized.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "question": {
                                "type": "string",
                                "description": "[Optional] The question to answer when producing the summary. (If omiitted, the entire page will be summarized)",
                            },
                            "url": {
                                "type": "string",
                                "description": "[Optional] The url of the page to summarize. (Defaults to current page)",
                            },
                        },
                    },
                    "required": [],
                }
            )
            # NOT QUITE READY YET
            # inner_llm_config["functions"].append(
            #    {
            #        "name": "semantic_find_on_page",
            #        "description": "Similar to standard Ctrl-F, semantic find-on-page will scroll to the part of the page most relevant to a question or query. It differs from standard find-on-page in that the match with the query terms need not be exact.",
            #        "parameters": {
            #            "type": "object",
            #            "properties": {
            #                "query": {
            #                    "type": "string",
            #                    "description": "[Optional] The query or search string to search for.",
            #                },
            #                "url": {
            #                    "type": "string",
            #                    "description": "[Optional] The url of the page on which to perform a semantic search. (Defaults to current page)",
            #                },
            #            },
            #        },
            #        "required": ["query"],
            #    }
            # )
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

        def _bing_search(query):
            self.browser.visit_page(f"bing: {query}")
            header, content = _browser_state()
            return header.strip() + "\n=======================\n" + content

        def _visit_wikipedia(topic_or_title):
            self.browser.visit_page(f"wikipedia: {topic_or_title}")
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
            return self.summarization_client.extract_text_or_function_call(response)[0]

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
                    "content": f"The following document includes line numbers. On which line would I find the information most relevant to the query '{query}'? Print both the line number (formatted as \"[Line 5]\" for example, including square brackets), and the content of the line itself. Here is the document:\n\n{buffer}",
                },
            ]

            response = self.summarization_client.create(context=None, messages=messages)
            response = self.summarization_client.extract_text_or_function_call(response)[0]

            m = re.search(r"\[\s*Line\s+(\d+)\s*]", response)
            if m:
                found_line = int(m.group(1))
                return _find_on_page(lines[found_line - 1])
            else:
                return response

        self._user_proxy.register_function(
            function_map={
                "bing_search": lambda query: _bing_search(query),
                "visit_page": lambda url: _visit_page(url),
                "page_up": lambda: _page_up(),
                "page_down": lambda: _page_down(),
                "find_on_page": lambda find_string: _find_on_page(find_string),
                "find_next_on_page": lambda: _find_next_on_page(),
                "visit_wikipedia": lambda topic_or_title: _visit_wikipedia(topic_or_title),
                "summarize_page": lambda question=None, url=None: _summarize_page(question, url),
                "semantic_find_on_page": lambda query=None, url=None: _semantic_find_on_page(query, url),
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
