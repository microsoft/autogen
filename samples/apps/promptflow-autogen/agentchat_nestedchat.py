import json
from typing import Any, Dict, List

import redis

import autogen
from autogen import Cache


class AgNestedChat:
    def __init__(self, redis_url: str, config_list: List[Dict[str, Any]]) -> None:
        # Initialize the workflows dictionary
        self.workflows = {}

        # Establish a connection to Redis
        self.redis_con = redis.from_url(redis_url)

        # Create a Redis cache with a seed of 16
        self.redis_cache = Cache.redis(cache_seed=16, redis_url=redis_url)

        # Store the configuration list
        self.config_list = config_list

        # Define the GPT-4 configuration
        self.llm_config = {
            "cache_seed": False,  # change the cache_seed for different trials
            "temperature": 0,
            "config_list": self.config_list,
            "timeout": 120,
        }

        # Initialize the writer agent
        self.writer = autogen.AssistantAgent(
            name="Writer",
            llm_config={"config_list": config_list},
            system_message="""
            You are a professional writer, known for your insightful and engaging articles.
            You transform complex concepts into compelling narratives.
            You should improve the quality of the content based on the feedback from the user.
            """,
        )

        # Initialize the user proxy agent
        self.user_proxy = autogen.UserProxyAgent(
            name="User",
            human_input_mode="NEVER",
            is_termination_msg=lambda x: x.get("content", "").find("TERMINATE") >= 0,
            code_execution_config={
                "last_n_messages": 1,
                "work_dir": "tasks",
                "use_docker": False,
            },  # Please set use_docker=True if docker is available to run the generated code. Using docker is safer than running the generated code directly.
        )

        # Initialize the critic agent
        self.critic = autogen.AssistantAgent(
            name="Critic",
            llm_config={"config_list": config_list},
            system_message="""
            You are a critic, known for your thoroughness and commitment to standards.
            Your task is to scrutinize content for any harmful elements or regulatory violations, ensuring
            all materials align with required guidelines.
            For code
            """,
        )

        # Register the reply function for each agent
        agents_list = [self.writer, self.user_proxy, self.critic]
        for agent in agents_list:
            agent.register_reply(
                [autogen.Agent, None],
                reply_func=self._update_redis,
                config={"callback": None},
            )

    def _update_redis(self, recipient, messages=[], sender=None, config=None):
        # Publish a message to Redis
        mesg = {"sender": sender.name, "receiver": recipient.name, "messages": messages}
        self.redis_con.publish("channel:1", json.dumps(mesg))
        return False, None

    def _reflection_message(self, recipient, messages, sender, config):
        # Generate a reflection message
        print("Reflecting...", "yellow")
        return f"Reflect and provide critique on the following writing. \n\n {recipient.chat_messages_for_summary(sender)[-1]['content']}"

    def chat(self, question: str) -> autogen.ChatResult:
        # Register nested chats for the user proxy agent
        self.user_proxy.register_nested_chats(
            [
                {
                    "recipient": self.critic,
                    "message": self._reflection_message,
                    "summary_method": "last_msg",
                    "max_turns": 1,
                }
            ],
            trigger=self.writer,  # condition=my_condition,
        )

        # Initiate a chat and return the result
        res = self.user_proxy.initiate_chat(
            recipient=self.writer,
            message=question,
            max_turns=2,
            summary_method="last_msg",
        )
        return res
