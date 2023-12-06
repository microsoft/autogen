import json
from dataclasses import dataclass
from typing import Dict, List, Optional, Union, Callable, Literal, Tuple
from autogen import Agent, ConversableAgent, AssistantAgent, UserProxyAgent, GroupChatManager, GroupChat, OpenAIWrapper
from autogen.browser_utils import SimpleTextBrowser
from autogen.code_utils import content_str
from datetime import datetime


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

        if browser_config is None:
            self.browser = SimpleTextBrowser()
        else:
            self.browser = SimpleTextBrowser(**browser_config)

        # Set the config to support function calling
        inner_llm_config = json.loads(json.dumps(llm_config))
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
            },
            {
                "name": "find_next_on_page",
                "description": "Find the next occurrence of a string on a the current webpage, and scroll to its position.",
                "parameters": {"type": "object", "properties": {}},
                "required": [],
            },
        ]

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

        self._user_proxy.register_function(
            function_map={
                "bing_search": lambda query: _bing_search(query),
                "visit_page": lambda url: _visit_page(url),
                "page_up": lambda: _page_up(),
                "page_down": lambda: _page_down(),
                "find_on_page": lambda find_string: _find_on_page(find_string),
                "find_next_on_page": lambda: _find_next_on_page(),
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
