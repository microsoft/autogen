import asyncio
from datetime import datetime
from typing import Awaitable, Callable
from autogen import config_list_from_json
from autogen import Agent, AssistantAgent, UserProxyAgent  # type: ignore[import-untyped], ConversableAgent
from autogen.coding import LocalCommandLineCodeExecutor

from ..database.database import ChatMessage, DatabaseManager
from ..files import FileManager


class AutoGenAgentManager:

    def __init__(self, llm_config: dict, db_manager: DatabaseManager, file_manager: FileManager):
        self._llm_config = llm_config or {"config_list": config_list_from_json("OAI_CONFIG_LIST")}
        self.db_manager = db_manager
        self.file_manager = file_manager

    async def generate_response(
        self, in_message: ChatMessage, out_message: ChatMessage, update_callback: Callable[[str], Awaitable[None]]
    ) -> ChatMessage:
        task = in_message.content
        executor = LocalCommandLineCodeExecutor(work_dir=self.file_manager.get_root_path())

        update_callback("Thinking...")

        def post_snippet_and_record_history(sender: Agent, message: str, recipient: Agent, silent: bool):

            update_callback(message[:100])

            sub_chat_message = ChatMessage(
                role="assistant" if sender.name == "assistant" else "user",
                content=message,
                root_id=out_message.id,
                timestamp=datetime.now().timestamp(),
            )

            self.db_manager.sync_set_chat_message(sub_chat_message)
            return message

        assistant = AssistantAgent("assistant", llm_config=self._llm_config)
        user = UserProxyAgent(
            "user",
            code_execution_config={"executor": executor},
            human_input_mode="NEVER",
            is_termination_msg=lambda x: x.get("content") and "TERMINATE" in x.get("content", ""),
        )
        assistant.register_hook("process_message_before_send", post_snippet_and_record_history)
        user.register_hook("process_message_before_send", post_snippet_and_record_history)

        update_callback("Starting agent conversation...")

        result = await user.a_initiate_chat(assistant, message=task, summary_method="reflection_with_llm")
        update_callback("Finishing up...")
        out_message.content = result.summary
        out_message.role = "assistant"
        return out_message
