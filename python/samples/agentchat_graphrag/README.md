# Building a Multi-Agent Application with AutoGen and GraphRAG

In this sample, we will build a chat interface that interacts with a `RoundRobinGroupChat` team built using the [AutoGen AgentChat](https://microsoft.github.io/autogen/dev/user-guide/agentchat-user-guide/index.html) API and the GraphRAG framework.


## High-Level Description

The `app.py` script sets up a chat interface that communicates with the AutoGen team. When a chat starts, it:

- Initializes an AgentChat team with both local and global search tools.
- As users interact with the chat, their queries are sent to the team which responds.
- As agents respond/act, their responses are streamed back to the chat interface.

## Setup

To set up the project, follow these steps:

1. Download the plain text version of "The Adventures of Sherlock Holmes" from [Project Gutenberg](https://www.gutenberg.org/ebooks/1661) and save it to `data/inputs/sherlock_book.txt`.

2. Run the `graphrag prompt-tune` command to tune the prompts. This step adjusts the prompts to better fit the context of the downloaded text.

3. After tuning, run the `graphrag index` command to index the data. This process will create the necessary data structures for performing searches.

The outputs will be located in the `data/` directory.

## Running the Sample

To run the sample, ensure you have set up an API Key. We will be using the OpenAI API for this example.

1. Ensure you have an OPENAPI API key. Set this key in your environment variables as `OPENAI_API_KEY`.

2. Install the required Python packages by running:

```bash
pip install -r requirements.txt
```

3. Run the sample by executing the following command:

```bash
python app.py
```
