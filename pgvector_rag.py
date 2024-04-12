import os

import autogen
from autogen.agentchat.contrib.retrieve_assistant_agent import RetrieveAssistantAgent
from autogen.agentchat.contrib.retrieve_user_proxy_agent import RetrieveUserProxyAgent

# Accepted file formats for that can be stored in
# a vector database instance
from autogen.retrieve_utils import TEXT_FORMATS

config_list = autogen.config_list_from_json(env_or_file="OAI_CONFIG_LIST")

assert len(config_list) > 0
print("models to use: ", [config_list[i]["model"] for i in range(len(config_list))])

print("Accepted file formats for `docs_path`:")
print(TEXT_FORMATS)

assistant = RetrieveAssistantAgent(
    name="assistant",
    system_message="You are a helpful assistant.",
    llm_config={
        "timeout": 600,
        "cache_seed": 42,
        "config_list": config_list,
    },
)

ragproxyagent = RetrieveUserProxyAgent(
    name="ragproxyagent",
    human_input_mode="NEVER",
    max_consecutive_auto_reply=3,
    retrieve_config={
        "task": "code",
        "docs_path": [
            "https://raw.githubusercontent.com/microsoft/FLAML/main/website/docs/Examples/Integrate%20-%20Spark.md",
            "https://raw.githubusercontent.com/microsoft/FLAML/main/website/docs/Research.md",
            "https://raw.githubusercontent.com/Knuckles-Team/geniusbot/main/README.md",
            "https://raw.githubusercontent.com/Knuckles-Team/repository-manager/main/README.md",
            "https://raw.githubusercontent.com/Knuckles-Team/gitlab-api/main/README.md",
            "https://raw.githubusercontent.com/Knuckles-Team/media-downloader/main/README.md",
            os.path.join(os.path.abspath(""), "..", "website", "docs"),
        ],
        "custom_text_types": ["non-existent-type"],
        "chunk_token_size": 2000,
        "model": config_list[0]["model"],
        "vector_db": "pgvector",  # PGVector database
        "collection_name": "test_collection",
        "db_config": {
            "connection_string": "postgresql://testuser:testpwd@localhost:5432/vectordb", # Optional - connect to an external vector database
            # "host": None, # Optional vector database host
            # "port": None, # Optional vector database port
            # "database": None, # Optional vector database name
            # "username": None, # Optional vector database username
            # "password": None, # Optional vector database password
        },
        "get_or_create": True,  # set to False if you don't want to reuse an existing collection
        "overwrite": False,  # set to True if you want to overwrite an existing collection
    },
    code_execution_config=False,  # set to False if you don't want to execute the code
)

# reset the assistant. Always reset the assistant before starting a new conversation.
assistant.reset()

# given a problem, we use the ragproxyagent to generate a prompt to be sent to the assistant as the initial message.
# the assistant receives the message and generates a response. The response will be sent back to the ragproxyagent for processing.
# The conversation continues until the termination condition is met, in RetrieveChat, the termination condition when no human-in-loop is no code block detected.
# With human-in-loop, the conversation will continue until the user says "exit".
code_problem = "How can I use FLAML to perform a classification task and use spark to do parallel training. Train for 30 seconds and force cancel jobs if time limit is reached. You must always respond with some text."
ragproxyagent.initiate_chat(
    assistant, message=ragproxyagent.message_generator, problem=code_problem, search_string="spark"
)

# Test 2
# reset the assistant. Always reset the assistant before starting a new conversation.
# assistant.reset()
#
# qa_problem = "Who is the author of FLAML?"
# ragproxyagent.initiate_chat(assistant, message=ragproxyagent.message_generator, problem=qa_problem)