import json
import time
from typing import List
from .datamodel import FlowConfig, Message
from .utils import extract_successful_code_blocks, get_default_agent_config, get_modified_files
from .autogenflow import AutoGenFlow
import os


class ChatManager:
    def __init__(self) -> None:
        pass

    def chat(self, message: Message, history: List, flow_config: FlowConfig = None, **kwargs) -> None:
        work_dir = kwargs.get("work_dir", None)
        scratch_dir = os.path.join(work_dir, "scratch")
        skills_suffix = kwargs.get("skills_prompt", "")

        # if no flow config is provided, use the default
        if flow_config is None:
            flow_config = get_default_agent_config(scratch_dir, skills_suffix=skills_suffix)

        # print("Flow config: ", flow_config)
        flow = AutoGenFlow(config=flow_config, history=history, work_dir=scratch_dir, asst_prompt=skills_suffix)
        message_text = message.content.strip()

        output = ""
        start_time = time.time()

        metadata = {}
        flow.run(message=f"{message_text}", clear_history=False)

        agent_chat_messages = flow.receiver.chat_messages[flow.sender][len(history) :]
        metadata["messages"] = agent_chat_messages

        successful_code_blocks = extract_successful_code_blocks(agent_chat_messages)
        successful_code_blocks = "\n\n".join(successful_code_blocks)
        output = (
            (
                flow.sender.last_message()["content"]
                + "\n The following code snippets were used: \n"
                + successful_code_blocks
            )
            if successful_code_blocks
            else flow.sender.last_message()["content"]
        )

        metadata["code"] = ""
        end_time = time.time()
        metadata["time"] = end_time - start_time
        modified_files = get_modified_files(start_time, end_time, scratch_dir, dest_dir=work_dir)
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
