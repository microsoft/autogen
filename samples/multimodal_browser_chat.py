import os
from autogen import Agent, ConversableAgent, OpenAIWrapper, config_list_from_json
from autogen.agentchat.contrib.multimodal_web_surfer import MultimodalWebSurferAgent
from autogen.code_utils import content_str
from typing import Any, Dict, List, Optional, Union, Callable, Literal, Tuple


def main():
    # Load LLM inference endpoints from an env variable or a file
    # See https://microsoft.github.io/autogen/docs/FAQ#set-your-api-endpoints
    # and OAI_CONFIG_LIST_sample.
    # For example, if you have created a OAI_CONFIG_LIST file in the current working directory, that file will be used.
    # NOTE: In this case, the LLM needs to be vision-capable
    llm_config_list = config_list_from_json(env_or_file="OAI_CONFIG_LIST", filter_dict={"tags": ["mlm"]})

    web_surfer = MultimodalWebSurferAgent(
        "web_surfer",
        llm_config={"config_list": llm_config_list},
        is_termination_msg=lambda x: x.get("content", "").rstrip().find("TERMINATE") >= 0,
        headless=True,
        browser_channel="chromium",
        browser_data_dir=None,
        start_page="about:blank",
        downloads_folder=os.getcwd(),
        debug_dir=os.path.join(os.getcwd(), "debug"),
    )

    mmagent = MultimodalAgent(
        "assistant",
        system_message="You are a general-purpose AI assistant and can handle many questions -- but you don't have access to a we boweser. However, the user you are talking to does have a browser, and you can see the screen. Provide short direct instructions to them to take you where you need to go to answer the initial question posed to you.",
        llm_config={"config_list": llm_config_list},
        human_input_mode="ALWAYS",
        is_termination_msg=lambda x: str(x.get("content", "")).find("TERMINATE") >= 0,
    )

    web_surfer.initiate_chat(mmagent, message="How can I help you today?")


class MultimodalAgent(ConversableAgent):
    def __init__(
        self,
        name: str,
        **kwargs,
    ):
        super().__init__(
            name=name,
            **kwargs,
        )

        self._reply_func_list = []
        self.register_reply([Agent, None], MultimodalAgent.generate_mlm_reply)
        self.register_reply([Agent, None], ConversableAgent.generate_code_execution_reply)
        self.register_reply([Agent, None], ConversableAgent.generate_function_call_reply)
        self.register_reply([Agent, None], ConversableAgent.check_termination_and_human_reply)

    def generate_mlm_reply(
        self,
        messages: Optional[List[Dict[str, str]]] = None,
        sender: Optional[Agent] = None,
        config: Optional[OpenAIWrapper] = None,
    ) -> Tuple[bool, Optional[Union[str, Dict[str, str]]]]:
        """Generate a reply using autogen.oai."""
        if messages is None:
            messages = self._oai_messages[sender]

        # Clone the messages to give context, but remove old screenshots
        history = []
        for i in range(0, len(messages) - 1):
            message = {}
            message.update(messages[i])
            message["content"] = content_str(message["content"])
            history.append(message)
        history.append(messages[-1])

        response = self.client.create(messages=self._oai_system_message + history)
        completion = self.client.extract_text_or_completion_object(response)[0]
        return True, completion


if __name__ == "__main__":
    main()
