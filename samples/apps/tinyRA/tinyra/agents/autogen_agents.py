from autogen import config_list_from_json
from autogen import AssistantAgent, UserProxyAgent  # type: ignore[import-untyped], ConversableAgent
from autogen.coding import LocalCommandLineCodeExecutor

from ..database.database import ChatMessage, DatabaseManager
from ..files import FileManager


class AutoGenAgentManager:

    def __init__(self, llm_config: dict, db_manager: DatabaseManager, file_manager: FileManager):
        self._llm_config = llm_config or {"config_list": config_list_from_json("OAI_CONFIG_LIST")}
        self.db_manager = db_manager
        self.file_manager = file_manager

    async def generate_response(self, in_message: ChatMessage, out_message: ChatMessage) -> ChatMessage:
        task = in_message.content
        executor = LocalCommandLineCodeExecutor(work_dir=self.file_manager.get_root_path())
        assistant = AssistantAgent("assistant", llm_config=self._llm_config)
        user = UserProxyAgent(
            "user",
            code_execution_config={"executor": executor},
            human_input_mode="NEVER",
            is_termination_msg=lambda x: x.get("content") and "TERMINATE" in x.get("content", ""),
        )
        result = await user.a_initiate_chat(assistant, message=task, summary_method="reflection_with_llm")
        out_message.content = result.summary
        out_message.role = "assistant"
        return out_message
