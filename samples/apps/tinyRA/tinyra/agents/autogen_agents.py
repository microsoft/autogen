import platform
import logging
from datetime import datetime
from typing import Awaitable, Callable
from autogen import config_list_from_json
from autogen import Agent, AssistantAgent, UserProxyAgent  # type: ignore[import-untyped], ConversableAgent
from autogen.coding import LocalCommandLineCodeExecutor
from autogen.coding.func_with_reqs import FunctionWithRequirements

from ..database.database import ChatMessage, DatabaseManager
from ..files import FileManager


class AutoGenAgentManager:

    name = "BasicTwoAgents"

    def __init__(self, llm_config: dict, db_manager: DatabaseManager, file_manager: FileManager):
        self._llm_config = llm_config or {"config_list": config_list_from_json("OAI_CONFIG_LIST")}
        self.db_manager = db_manager
        self.file_manager = file_manager
        self.logger = logging.getLogger(__name__)

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


class AGMPlusTools(AutoGenAgentManager):

    NAME = "BasicTwoAgents + Tools"

    async def get_system_message(self):
        user = await self.db_manager.get_user()
        user_name = user.name
        user_bio = user.bio
        user_preferences = user.preferences

        operating_system = platform.uname().system

        sys_message = f"""
        You are a helpful researcher assistant named "TinyRA".
        When introducing yourself do not forget your name!

        You are running on operating system with the following config:
        {operating_system}

        You are here to help "{user_name}" with his research.
        Their bio and preferences are below.

        The following is the bio of {user_name}:
        <bio>
        {user_bio}
        </bio>

        The following are the preferences of {user_name}.
        These preferences should always have the HIGHEST priority.
        And should never be ignored.
        Ignoring them will cause MAJOR annoyance.

        <preferences>{user_preferences}</preferences>

        Respond to {user_name}'s messages to be most helpful.

        """

        # append the autogen system message
        sys_message += "\nAdditional instructions:\n" + AssistantAgent.DEFAULT_SYSTEM_MESSAGE
        return sys_message

    async def generate_response(
        self, in_message: ChatMessage, out_message: ChatMessage, update_callback: Callable[[str], Awaitable[None]]
    ) -> ChatMessage:
        task = in_message.content

        tools = await self.db_manager.get_tools()
        functions = []
        for tool in tools:
            func = FunctionWithRequirements.from_str(tool.code)
            functions.append(func)
        executor = LocalCommandLineCodeExecutor(work_dir=self.file_manager.get_root_path(), functions=functions)

        update_callback("Thinking...")

        def terminate_on_consecutive_empty(recipient, messages, sender, **kwargs):
            # check the contents of the last N messages
            # if all empty, terminate
            consecutive_are_empty = None
            last_n = 2

            for message in reversed(messages):
                if last_n == 0:
                    break
                if message["role"] == "user":
                    last_n -= 1
                    if len(message["content"]) == 0:
                        consecutive_are_empty = True
                    else:
                        consecutive_are_empty = False
                        break

            if consecutive_are_empty:
                return True, "TERMINATE"

            return False, None

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

        assistant = AssistantAgent(
            "assistant",
            llm_config=self._llm_config,
            system_message=await self.get_system_message() + executor.format_functions_for_prompt(),
        )
        user = UserProxyAgent(
            "user",
            code_execution_config={"executor": executor},
            human_input_mode="NEVER",
            is_termination_msg=lambda x: x.get("content") and "TERMINATE" in x.get("content", ""),
        )

        # populate the history before registering new reply functions
        chat_history = await self.db_manager.get_chat_history(root_id=0)
        for msg in chat_history.messages:
            if msg.role == "user":
                user.send(msg.content, assistant, request_reply=False, silent=True)
            else:
                assistant.send(msg.content, user, request_reply=False, silent=True)

        assistant.register_reply([Agent, None], terminate_on_consecutive_empty)
        assistant.register_hook("process_message_before_send", post_snippet_and_record_history)
        user.register_hook("process_message_before_send", post_snippet_and_record_history)

        update_callback("Starting agent conversation...")

        await user.a_initiate_chat(assistant, message=task, clear_history=False)

        update_callback("Finishing up...")

        user.send(
            f"""Based on the results in above conversation, create a response for the user.
While computing the response, remember that this conversation was your inner mono-logue.
The user does not need to know every detail of the conversation.
All they want to see is the appropriate result for their task (repeated below) in
a manner that would be most useful.

The task was: {task}

There is no need to use the word TERMINATE in this response.
                """,
            assistant,
            request_reply=False,
            silent=True,
        )
        response = assistant.generate_reply(assistant.chat_messages[user], user)
        assistant.send(response, user, request_reply=False, silent=True)

        response = assistant.chat_messages[user][-1]["content"]

        out_message.content = response
        out_message.role = "assistant"
        return out_message


# def generate_response_process(msg_idx: int):
#     chat_history = fetch_chat_history()
#     task = chat_history[msg_idx]["content"]

#     def terminate_on_consecutive_empty(recipient, messages, sender, **kwargs):
#         # check the contents of the last N messages
#         # if all empty, terminate
#         consecutive_are_empty = None
#         last_n = 2

#         for message in reversed(messages):
#             if last_n == 0:
#                 break
#             if message["role"] == "user":
#                 last_n -= 1
#                 if len(message["content"]) == 0:
#                     consecutive_are_empty = True
#                 else:
#                     consecutive_are_empty = False
#                     break

#         if consecutive_are_empty:
#             return True, "TERMINATE"

#         return False, None

#     def summarize(text):
#         return text[:100]

#     def post_snippet_and_record_history(sender, message, recipient, silent):
#         if silent is True:
#             return message

#         if isinstance(message, str):
#             summary = message
#             insert_chat_message(sender.name, message, root_id=msg_idx + 1)
#         elif isinstance(message, Dict):
#             if message.get("content"):
#                 summary = message["content"]
#                 insert_chat_message(sender.name, message["content"], root_id=msg_idx + 1)
#             elif message.get("tool_calls"):
#                 tool_calls = message["tool_calls"]
#                 summary = "Calling tools…"
#                 insert_chat_message(sender.name, json.dumps(tool_calls), root_id=msg_idx + 1)
#             else:
#                 raise ValueError("Message must have a content or tool_calls key")

#         snippet = summarize(summary)
#         insert_chat_message("info", snippet, root_id=0, id=msg_idx + 1)
#         return message

#     tools = APP_CONFIG.get_tools()

#     functions = []
#     for tool in tools.values():
#         func = FunctionWithRequirements.from_str(tool.code)
#         functions.append(func)
#     executor = LocalCommandLineCodeExecutor(work_dir=APP_CONFIG.get_workdir(), functions=functions)

#     system_message = APP_CONFIG.get_assistant_system_message()
#     system_message += executor.format_functions_for_prompt()

#     assistant = AssistantAgent(
#         "assistant",
#         llm_config=LLM_CONFIG,
#         system_message=system_message,
#     )
#     user = UserProxyAgent(
#         "user",
#         code_execution_config={"executor": executor},
#         human_input_mode="NEVER",
#         is_termination_msg=lambda x: x.get("content") and "TERMINATE" in x.get("content", ""),
#     )

#     # populate the history before registering new reply functions
#     for msg in chat_history:
#         if msg["role"] == "user":
#             user.send(msg["content"], assistant, request_reply=False, silent=True)
#         else:
#             assistant.send(msg["content"], user, request_reply=False, silent=True)

#     assistant.register_reply([Agent, None], terminate_on_consecutive_empty)
#     assistant.register_hook("process_message_before_send", post_snippet_and_record_history)
#     user.register_hook("process_message_before_send", post_snippet_and_record_history)

#     logging.info("Current history:")
#     logging.info(assistant.chat_messages[user])

#     # hack to get around autogen's current api...
#     initial_reply = assistant.generate_reply(None, user)
#     assistant.initiate_chat(user, message=initial_reply, clear_history=False, silent=False)

#     # user.send(task, assistant, request_reply=True, silent=False)

#     user.send(
#         f"""Based on the results in above conversation, create a response for the user.
# While computing the response, remember that this conversation was your inner mono-logue. The user does not need to know every detail of the conversation.
# All they want to see is the appropriate result for their task (repeated below) in a manner that would be most useful.
# The task was: {task}

# There is no need to use the word TERMINATE in this response.
#         """,
#         assistant,
#         request_reply=False,
#         silent=True,
#     )
#     response = assistant.generate_reply(assistant.chat_messages[user], user)
#     assistant.send(response, user, request_reply=False, silent=True)

#     response = assistant.chat_messages[user][-1]["content"]

#     insert_chat_message("assistant", response, root_id=0, id=msg_idx + 1)
