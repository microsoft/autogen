import json
import time
from typing import List
import autogen
from .datamodel import AgentConfig, AgentFlowSpec, FlowConfig, LLMConfig, Message
from .utils import get_modified_files
from .autogenflow import AutoGenFlow


class ChatManager:
    def __init__(self) -> None:
        pass

    def chat(self, message: Message, history: List, **kwargs) -> None:
        work_dir = kwargs.get("work_dir", None)
        skills_suffix = kwargs.get("skills_prompt", "")

        USER_PROXY_INSTRUCTIONS = """If the request has been addressed sufficiently, summarize the answer and end with the word TERMINATE. Otherwise, ask a follow-up question.
        """

        llm_config = LLMConfig(
            seed=42,
            config_list=[{"model": "gpt-4"}],
            temperature=0,
        )

        userproxy_spec = AgentFlowSpec(
            type="userproxy",
            config=AgentConfig(
                name="user_proxy",
                human_input_mode="NEVER",
                system_message=USER_PROXY_INSTRUCTIONS,
                code_execution_config={
                    "work_dir": work_dir,
                    "use_docker": False,
                },
                max_consecutive_auto_reply=10,
                llm_config=llm_config,
                is_termination_msg=lambda x: x.get("content", "").rstrip().endswith("TERMINATE"),
            ),
        )

        assistant_spec = AgentFlowSpec(
            type="assistant",
            config=AgentConfig(
                name="primary_assistant",
                system_message=autogen.AssistantAgent.DEFAULT_SYSTEM_MESSAGE + skills_suffix,
                llm_config=llm_config,
            ),
        )

        flow_config = FlowConfig(
            name="default",
            sender=userproxy_spec,
            receiver=assistant_spec,
            type="default",
        )

        flow = AutoGenFlow(config=flow_config, history=history)
        message_text = message.content.strip()

        output = ""
        start_time = time.time()

        metadata = {}
        flow.run(message=message_text, clear_history=False)

        output = flow.sender.last_message()["content"]
        metadata["messages"] = flow.receiver.chat_messages[flow.sender][len(history) :]

        metadata["code"] = ""
        end_time = time.time()
        metadata["time"] = end_time - start_time
        modified_files = get_modified_files(start_time, end_time, work_dir)
        metadata["files"] = modified_files

        print("Modified files: ", modified_files)

        output_message = Message(
            user_id=message.user_id,
            root_msg_id=message.root_msg_id,
            role="assistant",
            content=output,
            metadata=json.dumps(metadata),
        )

        return output_message
