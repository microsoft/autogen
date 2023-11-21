import os
import sys
import pytest

from autogen import config_list_from_json
from autogen.agentchat.contrib.retrieve_assistant_agent import RetrieveAssistantAgent
from autogen.agentchat.contrib.mongoDB_retrieve_user_proxy_agent import MongoDBRetrieveUserProxyAgent, MongoDBConfig
import autogen

config_list = autogen.config_list_from_json(
    env_or_file="OAI_CONFIG_LIST",
    file_location=".",
    filter_dict={
        "model": {
            "gpt-3.5",
            # "gpt4",
            # "gpt-4",
            # "gpt-4-32k-0314",
            # "gpt-3.5-turbo",
        }
    },
)

assert len(config_list) > 0
print("models to use: ", [config_list[i]["model"] for i in range(len(config_list))])

# Define MongoDB configuration (replace with your own configuration)
mongo_config = MongoDBConfig(
    mongo_url="mongodb+srv://your_login:your_password@your_cluster?retryWrites=true&w=majority",
    database="your_database",
    vector_collection="your_vector_collection",
    vector_index="<your_vector_index>",
    embedding_field="<your_embedding_field-to-search>",
)

assistant = RetrieveAssistantAgent(
    name="assistant",
    system_message="You are a helpful assistant.",
    llm_config=config_list,
)

# Instantiate the User Proxy Agent with MongoDB functionality
ragproxyagent = MongoDBRetrieveUserProxyAgent(
    name="MongoDB_RAG_Agent",
    human_input_mode="NEVER",
    max_consecutive_auto_reply=2,
    retrieve_config={
        "task": "qa",
    },
    mongo_config=mongo_config,
)

# Reset the assistant and retrieve documents for a specific problem
assistant.reset()
ragproxyagent.initiate_chat(
    assistant,
    problem="when mifid was created?",
)
