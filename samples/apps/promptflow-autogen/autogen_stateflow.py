import json
import tempfile
from typing import Any, Dict, List

import redis

import autogen
from autogen import Cache
from autogen.coding import LocalCommandLineCodeExecutor


class AgStateFlow:
    def __init__(self, redis_url: str, config_list: List[Dict[str, Any]]) -> None:
        # Initialize the workflows dictionary
        self.workflows = {}

        # Establish a connection to Redis
        self.redis_con = redis.from_url(redis_url)

        # Create a Redis cache with a seed of 16
        self.redis_cache = Cache.redis(cache_seed=16, redis_url=redis_url)

        # Store the configuration list
        self.config_list = config_list

        # Create a temporary directory to store the code files
        self.temp_dir = tempfile.TemporaryDirectory()

        # Create a local command line code executor with a timeout of 10 seconds
        # and use the temporary directory to store the code files
        self.local_executor = LocalCommandLineCodeExecutor(timeout=10, work_dir=self.temp_dir.name)

        # Define the GPT-4 configuration
        self.gpt4_config = {
            "cache_seed": False,
            "temperature": 0,
            "config_list": self.config_list,
            "timeout": 120,
        }
        # Initialize the agents
        self.initializer = autogen.UserProxyAgent(
            name="Init",
            code_execution_config=False,
        )
        self.coder = autogen.AssistantAgent(
            name="Retrieve_Action_1",
            llm_config=self.gpt4_config,
            system_message="""You are the Coder. Given a topic, write code to retrieve related papers from the arXiv API, print their title, authors, abstract, and link.
        You write python/shell code to solve tasks. Wrap the code in a code block that specifies the script type. The user can't modify your code. So do not suggest incomplete code which requires others to modify. Don't use a code block if it's not intended to be executed by the executor.
        Don't include multiple code blocks in one response. Do not ask others to copy and paste the result. Check the execution result returned by the executor.
        If the result indicates there is an error, fix the error and output the code again. Suggest the full code instead of partial code or code changes. If the error can't be fixed or if the task is not solved even after the code is executed successfully, analyze the problem, revisit your assumption, collect additional info you need, and think of a different approach to try.
        """,
        )
        self.executor = autogen.UserProxyAgent(
            name="Retrieve_Action_2",
            system_message="Executor. Execute the code written by the Coder and report the result.",
            human_input_mode="NEVER",
            code_execution_config={"executor": self.local_executor},
        )
        self.scientist = autogen.AssistantAgent(
            name="Research_Action_1",
            llm_config=self.gpt4_config,
            system_message="""You are the Scientist. Please categorize papers after seeing their abstracts printed and create a markdown table with Domain, Title, Authors, Summary and Link""",
        )

        # Create the workflow
        self.create_workflow()

    def _state_transition(self, last_speaker, groupchat):
        messages = groupchat.messages

        # Define the state transitions
        if last_speaker is self.initializer:
            # init -> retrieve
            return self.coder
        elif last_speaker is self.coder:
            # retrieve: action 1 -> action 2
            return self.executor
        elif last_speaker is self.executor:
            if messages[-1]["content"] == "exitcode: 1":
                # retrieve --(execution failed)--> retrieve
                return self.coder
            else:
                # retrieve --(execution success)--> research
                return self.scientist
        elif last_speaker == "Scientist":
            # research -> end
            return None

    def _update_redis(self, recipient, messages=[], sender=None, config=None):
        # Publish a message to Redis
        mesg = {"sender": sender.name, "receiver": recipient.name, "messages": messages}
        self.redis_con.publish("channel:1", json.dumps(mesg))
        return False, None

    def create_workflow(self):
        # Register the reply function for each agent
        agents_list = [self.initializer, self.coder, self.executor, self.scientist]
        for agent in agents_list:
            agent.register_reply(
                [autogen.Agent, None],
                reply_func=self._update_redis,
                config={"callback": None},
            )

        # Create a group chat with the agents and define the speaker selection method
        self.groupchat = autogen.GroupChat(
            agents=agents_list,
            messages=[],
            max_round=20,
            speaker_selection_method=self._state_transition,
        )

        # Create a group chat manager
        self.manager = autogen.GroupChatManager(groupchat=self.groupchat, llm_config=self.gpt4_config)

    def chat(self, question: str):
        # Initiate a chat and return the result
        chat_result = self.initializer.initiate_chat(self.manager, message=question, cache=self.redis_cache)
        return chat_result
