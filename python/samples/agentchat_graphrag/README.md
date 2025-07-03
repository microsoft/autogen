# Building an AI Assistant Application with AutoGen and GraphRAG

In this sample, we will build a chat interface that interacts with an intelligent agent built using the [AutoGen AgentChat](https://microsoft.github.io/autogen/dev/user-guide/agentchat-user-guide/index.html) API and the GraphRAG framework.

## High-Level Description

The `app.py` script sets up a chat interface that communicates with an AutoGen assistant agent. When a chat starts, it:

- Initializes an AssistantAgent equipped with both local and global search tools from GraphRAG.
- The agent automatically selects the appropriate search tool based on the user's query.
- The selected tool queries the GraphRAG-indexed dataset and returns relevant information.
- The agent's responses are streamed back to the chat interface.

## What is GraphRAG?

GraphRAG (Graph-based Retrieval-Augmented Generation) is a framework designed to enhance AI systems by providing robust tools for information retrieval and reasoning. It leverages graph structures to organize and query data efficiently, enabling both global and local search capabilities.

Global Search: Global search involves querying the entire indexed dataset to retrieve relevant information. It is ideal for broad queries where the required information might be scattered across multiple documents or nodes in the graph.

Local Search: Local search focuses on a specific subset of the data, such as a particular node or neighborhood in the graph. This approach is used for queries that are contextually tied to a specific segment of the data.

By combining these search strategies, GraphRAG ensures comprehensive and context-sensitive responses from the AI assistant.

## Setup

To set up the project, follow these steps:

1. Install the required Python packages by running:

```bash
pip install -r requirements.txt
```

2. Navigate to this directory and run `graphrag init` to initialize the GraphRAG configuration. This command will create a `settings.yaml` file in the current directory.

3. _(Optional)_ Download the plain text version of "The Adventures of Sherlock Holmes" from [Project Gutenberg](https://www.gutenberg.org/ebooks/1661) and save it to `input/sherlock_book.txt`.

   **Note**: The app will automatically download this file if it doesn't exist when you run it, so this step is optional.

4. Set the `OPENAI_API_KEY` environment variable with your OpenAI API key:

```bash
export OPENAI_API_KEY='your-api-key-here'
```

Alternatively, you can update the `.env` file with the API Key that will be used by GraphRAG:

```bash
GRAPHRAG_API_KEY=your_openai_api_key_here
```

5. Adjust your [GraphRAG configuration](https://microsoft.github.io/graphrag/config/yaml/) in the `settings.yaml` file with your LLM and embedding configuration. Ensure that the API keys and other necessary details are correctly set.

6. Create a `model_config.yaml` file with the Assistant model configuration. Use the `model_config_template.yaml` file as a reference. Make sure to remove the comments in the template file.

7. Run the `graphrag prompt-tune` command to tune the prompts. This step adjusts the prompts to better fit the context of the downloaded text.

8. After tuning, run the `graphrag index` command to index the data. This process will create the necessary data structures for performing searches. The indexing may take some time, at least 10 minutes on most machines, depending on the connection to the model API.

The outputs will be located in the `output/` directory.

## Running the Sample

Run the sample by executing the following command:

```bash
python app.py
```

The application will:

1. Check for the required `OPENAI_API_KEY` environment variable
2. Automatically download the Sherlock Holmes book if it doesn't exist in the `input/` directory
3. Initialize both global and local search tools from your GraphRAG configuration
4. Create an assistant agent equipped with both search tools
5. Run a demonstration query: "What does the station-master say about Dr. Becher?"

The agent will automatically select the appropriate search tool (in this case, local search for specific entity information) and provide a detailed response based on the indexed data.

You can modify the hardcoded query in `app.py` line 79 to test different types of questions:

- **Global search examples**: "What are the main themes in the stories?" or "What is the overall sentiment?"
- **Local search examples**: "What does character X say about Y?" or "What happened at location Z?"
