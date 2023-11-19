import os
import sys
import pytest
print(sys.path)
sys.path.append('/Users/han.heloir/Library/CloudStorage/GoogleDrive-han.heloir@mongodb.com/My Drive/03 Demos_jaime/AIDEMOS/autogen/autogen/')

from retrieve_assistant_agent import RetrieveAssistantAgent
from autogen import config_list_from_json
#from autogen.agentchat.contrib.retrieve_assistant_agent import RetrieveAssistantAgent
from mongoDB_retrieve_user_proxy_agent import MongoDBRetrieveUserProxyAgent

#from autogen.agentchat.contrib.t import MongoDBRetrieveUserProxyAgent

# Import the classes and functions from the refactored code
#from autogen.agentchat.contrib.mongoDB_retrieve_user_proxy_agent import MongoDBRetrieveUserProxyAgent, MongoDBConfig
try:
    from mongoDB_retrieve_user_proxy_agent import (
        MongoDBRetrieveUserProxyAgent, 
        MongoDBConfig
    )
    
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


# Define MongoDB configuration (replace with your own configuration)
""" mongo_config = MongoDBConfig(
    mongo_url="mongodb+srv://your_login:your_password@your_cluster?retryWrites=true&w=majority",
    database="your_database",
    vector_collection="your_vector_collection",
    vector_index="<your_vector_index>",
    embedding_field="<your_embedding_field-to-search>",
) """

mongo_config = MongoDBConfig(
    mongo_url="mongodb+srv://han:han@cluster0.bofm7.mongodb.net/?retryWrites=true&w=majority",
    database="AIRegulation",
    vector_collection="mifid2",
    vector_index="default",
    embedding_field="ada_embedding",
)

assistant = RetrieveAssistantAgent(
    name="assistant",
    system_message="You are a helpful assistant.",
    # llm_config=config_list,
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
