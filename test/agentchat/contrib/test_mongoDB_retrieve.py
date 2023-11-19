import os
import sys
import pytest
import sys

from autogen import config_list_from_json
from autogen.agentchat.contrib.retrieve_assistant_agent import RetrieveAssistantAgent

from autogen.agentchat.contrib.mongoDB_retrieve_user_proxy_agent import MongoDBRetrieveUserProxyAgent

# Import the classes and functions from the refactored code
try:
    from autogen.agentchat.contrib.mongoDB_retrieve_user_proxy_agent import (MongoDBRetrieveUserProxyAgent, MongoDBConfig)
    import pymongo
    MONGODB_INSTALLED = True
except ImportError:
    MONGODB_INSTALLED = False

# Define MongoDB configuration (replace with your own configuration)
# mongo_config = MongoDBConfig(
#     mongo_url="mongodb+srv://your_login:your_password@your_cluster?retryWrites=true&w=majority",
#     database="your_database",
#     vector_collection="your_vector_collection",
#     vector_index="<your_vector_index>",
#     embedding_field="<your_embedding_field-to-search>",
# )

mongo_config = MongoDBConfig(
    mongo_url="mongodb+srv://han:han@cluster0.bofm7.mongodb.net/?retryWrites=true&w=majority",
    database="AIRegulation",
    vector_collection="mifid2",
    vector_index="default",
    embedding_field="ada_embedding",
)

# Create an instance of MongoDBRetrieveUserProxyAgent with MongoDB configuration
mongo_agent = MongoDBRetrieveUserProxyAgent(mongo_config)

# Test the retrieve_docs method
problem_to_search = "When mifi2 was created"
results = mongo_agent.retrieve_docs(problem_to_search, n_results=5)

assistant = RetrieveAssistantAgent(
    name="assistant",
    system_message="You are a helpful assistant.",
    #llm_config=config_list,
)

# Instantiate the User Proxy Agent with MongoDB functionality
ragproxyagent = MongoDBRetrieveUserProxyAgent(
    name="MongoDB_RAG_Agent",
    human_input_mode="NEVER",
    max_consecutive_auto_reply=2,
    retrieve_config={
        "task": "qa",
    },
    mongo_config = mongo_config,
)

# Reset the assistant and retrieve documents for a specific problem
assistant.reset()
ragproxyagent.initiate_chat(
    assistant,
    #problem="What is the average price of client A's expense based on his purchase history provided?",
    problem="when mifid was created?",
)