import json
import time
from typing import List
from .datamodel import Message
import autogen
from .utils import get_modified_files

class ChatManager():

    def __init__(self) -> None:
        pass 
 

    def chat(self, message: Message, history: List, **kwargs) -> None:
        message_text = message.content.strip()
        execute_code = "@execute" in message_text 
        human_input_mode = "NEVER" 

        work_dir = kwargs.get("work_dir", None)
        user_dir = kwargs.get("user_dir", None)

        config_list = autogen.config_list_from_json(
            env_or_file="OAI_CONFIG_LIST"
        )

        llm_config = { 
            "seed": 42,  # change the seed for different trials
            "config_list": config_list,
            "temperature": 0,
        }

        user_proxy = autogen.UserProxyAgent(
            name="user_proxy",
            human_input_mode=human_input_mode,
            code_execution_config={
                "work_dir": work_dir,
                "use_docker": False,
            },
            max_consecutive_auto_reply=10,
            llm_config=llm_config,
            is_termination_msg=lambda x: x.get("content", "").rstrip().endswith("TERMINATE"),
        )

        skills_suffix = ""
        primary_assistant = autogen.AssistantAgent(
            name="primary_assitant",
            system_message=autogen.AssistantAgent.DEFAULT_SYSTEM_MESSAGE + skills_suffix,
            llm_config= llm_config,
        )

        # populate the agent mssage history 
        for msg in history:
            if msg["role"] == "user":
                user_proxy.send(
                    msg["content"],
                    primary_assistant,
                    request_reply=False, 
                )
            elif msg["role"] == "assistant":
                primary_assistant.send(
                    msg["content"],
                    user_proxy,
                    request_reply=False, 
                )
        output = ""

        start_time = time.time()
         
        metadata = {}
        if execute_code and len(history) > 0:
            # if history[-1]["role"] == "assistant":
            primary_assistant.initiate_chat(
                user_proxy,
                message = history[-1]["content"],
                clear_history=False,
            ) 
             
            output = user_proxy.last_message()["content"]
            metadata["messages"] = primary_assistant.chat_messages[user_proxy][len(history):]
             
        else:
            user_proxy.send(
                message_text,
                primary_assistant,
                request_reply=True, 
            ) 
            output = user_proxy.last_message()["content"]
            metadata["messages"] = primary_assistant.chat_messages[user_proxy][len(history):]
             
        metadata["code"] = ""
        end_time = time.time()
        modified_files = get_modified_files(start_time, end_time, work_dir, user_dir)
        metadata["files"] = modified_files

        print("Modified files: ", modified_files)
         
        output_message = Message(
            userId = message.userId,
            rootMsgId=message.rootMsgId, 
            role="assistant",
            content=output,
            metadata=json.dumps(metadata) 
        )

        

        return output_message

