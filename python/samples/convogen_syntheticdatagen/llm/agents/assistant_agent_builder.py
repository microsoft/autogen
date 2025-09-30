import os
import os
import pandas as pd
import json
from dotenv import load_dotenv
from autogen import  AssistantAgent
import re


from llm.models.settings import open_ai_ep,open_ai_api_deployment_name,open_ai_api_version


class AssistantAgentBuilder:
    def __init__(self, individual_config=None):
        self.config_list = [
            {
                "model": open_ai_api_deployment_name,
                "api_type": "azure",
                "base_url": open_ai_ep,
                "api_version": open_ai_api_version,
                "azure_ad_token_provider": "DEFAULT"
            }
        ]

        self.name = "agent"
        if individual_config is not None:
            self.individual_config = individual_config
            self.name = self.individual_config.get("name","agent")
            # remove any spaces in the name
            self.name = self.name.replace(" ","-")
            self.name = re.sub(r"[^a-zA-Z0-9_\- ]", " ", self.name)
            self.persona = self.individual_config.get("persona",None)
            # to fix the format of some personas
            
            if self.persona is None:
                self.qualities = self.individual_config.get("qualities",[])
                self.speech_style = self.individual_config.get("speechStyle",'like a youtube video host')
                self.age = self.individual_config.get("age",25)
                self.life_style = self.individual_config.get("lifestyle","")
                self.memory = self.individual_config.get("memory","")
            else:
                self.persona = re.sub(r"^[0-9]+ - ", "", self.persona)
                
            self.system_message = self._build_system_message()
            self.description = self._build_description()

    def _build_system_message(self):
        system_message = f"You are {self.name}. "
        if self.persona is None:
            system_message += f"You are {self.age} years old. Your speech style is {self.speech_style}."
            if len(self.qualities) > 0:
                system_message += f" You are {', '.join(self.qualities)}."
            if self.life_style != "":
                system_message += f" You have this life style: {self.life_style}."
            if self.memory != "":
                system_message += f" Your keep the following in your memory: {self.memory}.\n\n"
        else:
            system_message += f"You have the following persona: {self.persona}.\n\n"
        system_message += " You participate in a conversation and provide responses to the other speakers in the conversation. You can see everyone in the conversation, so no need to address the speakers by their names. You must sound natural in your speech. You can also express your promises." + """
        ## Guidelines for the conversation:
        - You don't need to address the other speakers by their names. You don't need to speak to everyone in the conversation. For example you can say "I think that's a great idea." instead of "I think that's a great idea, John.". This makes the conversation more natural.
        - You can ask questions, provide answers, and make comments.
        - You can also provide information and share your opinions.
        - Never sound artificial or robotic. For example, instead of saying "Your project sounds fascinating, Lucas.", you can say "fascinating, yeah".
        - You can stop the conversation at any time by saying "I have to go now." or "I have to leave now. You can only say that once and then leave the conversation. If you say any of these exit statements, you will not be able to return to the conversation or speak again."
        - You can pause in the middle of the conversation by saying "I need a ", to allow other speakers to interrupt you.
        - You can interrupt other speakers by saying "I have something to say." or "I have a question."
        - You can express your promises by saying "I will do that." or "I promise to do that."
        - YOu don't need to start with confimation words like "yes" or "okay" or "Absolutely". You can start with the main content of your response, so that you can sound more natural.
        - You must be concise and limit your response to 30 tokens at most.
        """
        self.system_message = system_message
        return system_message
    
    def _build_description(self):
        description = f"Your name is {self.name}. "
        if self.persona is None:
            description += f"You are {self.age} years old. You are {self.speech_style}. You are {', '.join(self.qualities)}. You have this work and hobbies: {self.life_style}."
        else:
            description += f"You have the following persona: {self.persona}."
        return description


    def introduce(self):
        return f"Name: {self.name}. Role: {self.system_message}"
    
    def build(self):
        return AssistantAgent(
            name=self.name,
            system_message=self.system_message,
            description = self.description,
            llm_config={"config_list": self.config_list},
        )