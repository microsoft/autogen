import pandas as pd
import os
import numpy as np
import json
from llm.agents.assistant_agent_builder import AssistantAgentBuilder
from autogen import UserProxyAgent,GroupChat,GroupChatManager

from llm.models.settings import open_ai_ep,open_ai_api_deployment_name,open_ai_api_version

import uuid


class GroupChatBuilder:
    def __init__(self, situation_config=None, experiment_name="Default", run_name="run-default", max_turns=12, min_turns=10, deployment_name=None, base_output_path="output", ignore_agents_list=["User_proxy"]):
        if deployment_name is None:
            deployment_name = open_ai_api_deployment_name

        self.config_list = [
            {
                "model": deployment_name,
                "api_type": "azure",
                # "azure_ad_token": token,
                "base_url": open_ai_ep,
                "api_version": open_ai_api_version,
                "azure_ad_token_provider": "DEFAULT"
            }
        ]

        self.output_path = os.path.join(base_output_path, experiment_name, run_name)

        self.max_turns = max_turns
        self.min_turns = min_turns
        self.num_turns = np.random.randint(self.min_turns, self.max_turns+1)
        self.ignore_agents_list = ignore_agents_list
        self.situation_config = situation_config
        # parse the conversation group config
        self._parse_situation_config()
        # build the initial message for the conversation
        self.initial_message = self._build_initial_message()
        # Initialize the main conversation participants
        assistant_agent_builders = [ AssistantAgentBuilder(individual_config=individual_config) for individual_config in self.individuals ]
        self.assistant_agents = [ assistant_agent_builder.build() for assistant_agent_builder in assistant_agent_builders ]
        # Initialize the user proxy
        self.user_proxy = self._init_user_proxy()

        self.agents =  self.assistant_agents + [self.user_proxy]
        # Initialize the speaker selection message template
        self.select_speaker_message_template = self._init_speaker_selection_message_template()
        # Initialize the speaker selection prompt
        self.select_speaker_prompt_template = self._init_speaker_selection_prompt()
        # Initialize the group chat
        self.group_chat = self._init_group_chat()
        self.manager = GroupChatManager(self.group_chat, llm_config=self.config_list[0],silent=False)

    def _parse_situation_config(self):
        self.individuals = self.situation_config.get("individuals",[])
        # for the relations and ties between the individuals
        self.relations = self.situation_config.get("relations",[])
        # for a hypothetical situation or context for the conversation
        self.situation = self.situation_config.get("situation","")
        # topic for the conversation
        self.topic = self.situation_config.get("topic","")
        # starter for the conversation
        self.starter = self.situation_config.get("conversationStarter","")

    def _build_initial_message(self):
        initial_message = f"Welcome to the group chat. The topic of the conversation is {self.topic}. The situation is: {self.situation}. The relation between the individuals can be summarized as: {self.relations}.\n"
        if self.starter != "":
            initial_message += f" Start a conversation about '{self.topic}' using this conversation starter: {self.starter}."
        initial_message += "\n\n"
        return initial_message

    def _init_user_proxy(self):
        # The description is used for speaker selection in the conversation
        user_proxy_description = "A third person who starts the conversation and listens to the conversation between multiple people, without participating in the conversation."
        user_proxy_system_message = "A third person who starts the conversation and listens to the conversation between multiple people, without participating in the conversation."
        user_proxy = UserProxyAgent(
        name="User_proxy",
        description=user_proxy_description,
        system_message=user_proxy_system_message,
        code_execution_config=False, 
        human_input_mode="NEVER")
        return user_proxy
    
    def _init_speaker_selection_message_template(self):
        speaker_select_msg = """You are a third person listening to a conversation between multiple persons, and their roles are: {roles}. You must only listen without speaking. You must never interfere in the conversation. Read the following conversation. Then select the next role from {agentlist} to play. Only return the role."""
        return speaker_select_msg
    
    def _init_speaker_selection_prompt(self):
        situation =  " situation: {0} \n relations: {1} \n topic: {2}\n ".format(self.situation, self.relations, self.topic).replace("{","{{").replace("}","}}")
        speaker_select_prompt = situation + """Read the above conversation. Then select the next role from {agentlist} to speak. Do not explain why. Only return the role."""
        return speaker_select_prompt
    
    def _init_group_chat(self):
        group_chat = GroupChat(agents=self.agents, messages=[], max_round=self.num_turns, select_speaker_message_template=self.select_speaker_message_template, select_speaker_prompt_template=self.select_speaker_prompt_template)
        return group_chat
    
    def _format_messages(self, chat):
        conversation = []
        speakerMap = {}
        counter = 1
        for message in chat:
            content, _, name = message.values()
            if name in self.ignore_agents_list:
                continue
            if name not in speakerMap:
                speakerMap[name] = f"Guest{counter}"
                counter += 1
            content = content.split(":")[-1].strip() # fix cases where the speaker name is included in the message
            conversation.append({"speaker": speakerMap[name], "transcript": content})
        return conversation, speakerMap
    
    def _format_chat(self, chat):
        meetingID = str(uuid.uuid4())
        conversation, speakerMap = self._format_messages(chat)
        conversation = json.loads(json.dumps(conversation))
        speakerMap = json.loads(json.dumps(speakerMap))
        situation_config = json.loads(json.dumps(self.situation_config))
        data = {"meetingID": meetingID, "speakerMap": speakerMap, "Conversation": conversation, "situation_config": situation_config}
        data = json.loads(json.dumps(data))
        return data
    
    def _save_chat(self, chat):
        if not os.path.exists(self.output_path):
            os.makedirs(self.output_path)
        meetingID = chat["meetingID"]
        filepath = os.path.join(self.output_path, f"chat-{meetingID}.json")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(chat, f, indent=4, ensure_ascii=False)
  
    def start_conversation(self, save_output=False):
        try:
            self.user_proxy.initiate_chat(self.manager, message=self.initial_message)
            chat = self.manager.groupchat.messages
            chat = self._format_chat(chat)
            if save_output:
                self._save_chat(chat)
            return chat
        except Exception as e:
            print(f"Error in generating the group chat: {e}")
            return None


