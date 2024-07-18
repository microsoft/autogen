# Retrieval Augmentation

Retrieval Augmented Generation (RAG) is a powerful technique that combines language models with external knowledge retrieval to improve the quality and relevance of generated responses.

One way to realize RAG in AutoGen is to construct agent chats with `RetrieveAssistantAgent` and `RetrieveUserProxyAgent` classes.

## Example Setup: RAG with Retrieval Augmented Agents
The following is an example setup demonstrating how to create retrieval augmented agents in AutoGen:

### Step 1. Create an instance of `RetrieveAssistantAgent` and `RetrieveUserProxyAgent`.

Here `RetrieveUserProxyAgent` instance acts as a proxy agent that retrieves relevant information based on the user's input.
```python
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
            os.path.join(os.path.abspath(""), "..", "website", "docs"),
        ],
        "custom_text_types": ["mdx"],
        "chunk_token_size": 2000,
        "model": config_list[0]["model"],
        "client": chromadb.PersistentClient(path="/tmp/chromadb"),
        "embedding_model": "all-mpnet-base-v2",
        "get_or_create": True,  # set to False if you don't want to reuse an existing collection, but you'll need to remove the collection manually
    },
    code_execution_config=False,  # set to False if you don't want to execute the code
)
```

### Step 2. Initiating Agent Chat with Retrieval Augmentation

Once the retrieval augmented agents are set up, you can initiate a chat with retrieval augmentation using the following code:

```python
code_problem = "How can I use FLAML to perform a classification task and use spark to do parallel training. Train 30 seconds and force cancel jobs if time limit is reached."
ragproxyagent.initiate_chat(
    assistant, message=ragproxyagent.message_generator, problem=code_problem, search_string="spark"
)  # search_string is used as an extra filter for the embeddings search, in this case, we only want to search documents that contain "spark".
```

## Example Setup: RAG with Retrieval Augmented Agents with PGVector
The following is an example setup demonstrating how to create retrieval augmented agents in AutoGen:

### Step 1. Create an instance of `RetrieveAssistantAgent` and `RetrieveUserProxyAgent`.

Here `RetrieveUserProxyAgent` instance acts as a proxy agent that retrieves relevant information based on the user's input.

Specify the connection_string, or the host, port, database, username, and password in the db_config.

```python
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
            os.path.join(os.path.abspath(""), "..", "website", "docs"),
        ],
        "vector_db": "pgvector",
        "collection_name": "autogen_docs",
        "db_config": {
            "connection_string": "postgresql://testuser:testpwd@localhost:5432/vectordb", # Optional - connect to an external vector database
            # "host": None, # Optional vector database host
            # "port": None, # Optional vector database port
            # "database": None, # Optional vector database name
            # "username": None, # Optional vector database username
            # "password": None, # Optional vector database password
        },
        "custom_text_types": ["mdx"],
        "chunk_token_size": 2000,
        "model": config_list[0]["model"],
        "get_or_create": True,
    },
    code_execution_config=False,
)
```

### Step 2. Initiating Agent Chat with Retrieval Augmentation

Once the retrieval augmented agents are set up, you can initiate a chat with retrieval augmentation using the following code:

```python
code_problem = "How can I use FLAML to perform a classification task and use spark to do parallel training. Train 30 seconds and force cancel jobs if time limit is reached."
ragproxyagent.initiate_chat(
    assistant, message=ragproxyagent.message_generator, problem=code_problem, search_string="spark"
)  # search_string is used as an extra filter for the embeddings search, in this case, we only want to search documents that contain "spark".
```

## Online Demo
[Retrival-Augmented Chat Demo on Huggingface](https://huggingface.co/spaces/thinkall/autogen-demos)

## More Examples and Notebooks
For more detailed examples and notebooks showcasing the usage of retrieval augmented agents in AutoGen, refer to the following:
- Automated Code Generation and Question Answering with Retrieval Augmented Agents - [View Notebook](/docs/notebooks/agentchat_RetrieveChat)
- Automated Code Generation and Question Answering with [PGVector](https://github.com/pgvector/pgvector) based Retrieval Augmented Agents - [View Notebook](https://github.com/microsoft/autogen/blob/main/notebook/agentchat_RetrieveChat_pgvector.ipynb)
- Automated Code Generation and Question Answering with [Qdrant](https://qdrant.tech/) based Retrieval Augmented Agents - [View Notebook](https://github.com/microsoft/autogen/blob/main/notebook/agentchat_RetrieveChat_qdrant.ipynb)
- Chat with OpenAI Assistant with Retrieval Augmentation - [View Notebook](https://github.com/microsoft/autogen/blob/main/notebook/agentchat_oai_assistant_retrieval.ipynb)
- **RAG**: Group Chat with Retrieval Augmented Generation (with 5 group member agents and 1 manager agent) - [View Notebook](/docs/notebooks/agentchat_groupchat_RAG)

## Roadmap

Explore our detailed roadmap [here](https://github.com/microsoft/autogen/issues/1657) for further advancements plan around RAG. Your contributions, feedback, and use cases are highly appreciated! We invite you to engage with us and play a pivotal role in the development of this impactful feature.
