# Building a Multi-Agent Application with AutoGen and GraphRAG

In this sample, we will build a chat interface that interacts with a `RoundRobinGroupChat` team built using the [AutoGen AgentChat](https://microsoft.github.io/autogen/dev/user-guide/agentchat-user-guide/index.html) API and the GraphRAG framework.


## High-Level Description

The `app.py` script sets up a chat interface that communicates with the AutoGen team. When a chat starts, it:

- Initializes an AgentChat team with both local and global search tools.
- As user query is sent to the team with the agent, which must select the appropriate tool to use, the query is then passed to the appropriate tool to respond.
- As agents respond/act, their responses are streamed back to the chat interface.

## What is GraphRAG?

GraphRAG (Graph-based Retrieval-Augmented Generation) is a framework designed to enhance multi-agent systems by providing robust tools for information retrieval and reasoning. It leverages graph structures to organize and query data efficiently, enabling both global and local search capabilities.

Global Search: Global search involves querying the entire indexed dataset to retrieve relevant information. It is ideal for broad queries where the required information might be scattered across multiple documents or nodes in the graph.

Local Search: Local search focuses on a specific subset of the data, such as a particular node or neighborhood in the graph. This approach is used for queries that are contextually tied to a specific segment of the data.

By combining these search strategies, GraphRAG ensures comprehensive and context-sensitive responses from the multi-agent team.


## Setup

To set up the project, follow these steps:

1. Install the required Python packages by running:

```bash
pip install -r requirements.txt
```

2. Download the plain text version of "The Adventures of Sherlock Holmes" from [Project Gutenberg](https://www.gutenberg.org/ebooks/1661) and save it to `data/input/sherlock_book.txt`.

3. Adjust the `settings.yaml` file with your LLM and embedding configuration. Ensure that the API keys and other necessary details are correctly set.

4. Create a `model_config.yaml` file with the Assistant model configuration. Use the `model_config_template.yaml` file as a reference. Make sure to remove the comments in the template file. 

5. Run the `graphrag prompt-tune` command to tune the prompts. This step adjusts the prompts to better fit the context of the downloaded text.

6. After tuning, run the `graphrag index` command to index the data. This process will create the necessary data structures for performing searches. The indexing may take some time, at least 10 minutes on most machines, depending on the connection to the model API.

The outputs will be located in the `data/output/` directory.

## Running the Sample

Run the sample by executing the following command:

```bash
python app.py

Agent response: [FunctionCall(id='call_0xAXMOHLl62QFd9cfIb0S3BO', arguments='{"query":"station-master Dr. Becher"}', name='local_search_tool')]

Agent response: [FunctionExecutionResult(content='{"answer": "### Dr. Becher and the Station-Master\\n\\nDr. Becher is an Englishman who owns a house that caught fire, and he has a foreign patient staying with him [Data: Entities (489)]. The fire at Dr. Becher\'s house was a significant event, as it was described as a great widespread whitewashed building spouting fire at every chink and window, with fire-engines striving to control the blaze [Data: Sources (91); Entities (491)]. The station-master provided information about the fire, confirming that it broke out during the night and worsened, leading to the entire place being in a blaze [Data: Sources (91)].\\n\\nThe station-master also clarified a misunderstanding about Dr. Becher\'s nationality, stating that Dr. Becher is an Englishman, contrary to the engineer\'s assumption that he might be a German. The station-master humorously noted that Dr. Becher is well-fed, unlike his foreign patient, who could benefit from some good Berkshire beef [Data: Sources (91)].\\n\\n### The Fire Incident\\n\\nThe fire at Dr. Becher\'s house was linked to a larger criminal investigation involving a gang of coiners. The fire was inadvertently started by an oil-lamp that was crushed in a press, which was part of the machinery used by the gang. This incident was a turning point in the investigation, as it led to the discovery of the gang\'s operations, although the criminals managed to escape [Data: Sources (91)].\\n\\nThe fire-engines present at the scene were unable to prevent the destruction of the house, and the firemen were perturbed by the strange arrangements they found within the building. Despite their efforts, the house was reduced to ruins, with only some twisted cylinders and iron piping remaining [Data: Sources (91); Entities (491)].\\n\\nIn summary, Dr. Becher\'s house fire was a pivotal event in the investigation of a criminal gang, with the station-master providing key information about the incident and Dr. Becher\'s identity. The fire not only highlighted the dangers associated with the gang\'s activities but also underscored the challenges faced by law enforcement in apprehending the criminals."}', call_id='call_0xAXMOHLl62QFd9cfIb0S3BO')]
```
