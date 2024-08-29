# What is Promptflow

Promptflow is a comprehensive suite of tools that simplifies the development, testing, evaluation, and deployment of LLM based AI applications. It also supports integration with Azure AI for cloud-based operations and is designed to streamline end-to-end development.

Refer to [Promptflow docs](https://microsoft.github.io/promptflow/) for more information.

Quick links:

- Why use Promptflow - [Link](https://learn.microsoft.com/en-us/azure/machine-learning/prompt-flow/overview-what-is-prompt-flow)
- Quick start guide - [Link](https://microsoft.github.io/promptflow/how-to-guides/quick-start.html)

## Getting Started

- Install required python packages

  ```bash
  cd samples/apps/promptflow-autogen
  pip install -r requirements.txt
  ```

- This example assumes a working Redis cache service to be available. You can get started locally using this [guide](https://redis.io/docs/latest/operate/oss_and_stack/install/install-redis/) or use your favorite managed service

## Chat flow

Chat flow is designed for conversational application development, building upon the capabilities of standard flow and providing enhanced support for chat inputs/outputs and chat history management. With chat flow, you can easily create a chatbot that handles chat input and output.

## Create connection for LLM tool to use

You can follow these steps to create a connection required by a LLM tool.

Currently, there are two connection types supported by LLM tool: "AzureOpenAI" and "OpenAI". If you want to use "AzureOpenAI" connection type, you need to create an Azure OpenAI service first. Please refer to [Azure OpenAI Service](https://azure.microsoft.com/en-us/products/cognitive-services/openai-service/) for more details. If you want to use "OpenAI" connection type, you need to create an OpenAI account first. Please refer to [OpenAI](https://platform.openai.com/) for more details.

```bash
# Override keys with --set to avoid yaml file changes

# Create Azure open ai connection
pf connection create --file azure_openai.yaml --set api_key=<your_api_key> api_base=<your_api_base> --name open_ai_connection

# Create the custom connection for Redis Cache
pf connection create -f custom_conn.yaml --set secrets.redis_url=<your-redis-connection-url> --name redis_connection_url
# Sample redis connection string rediss://:PASSWORD@redis_host_name.redis.cache.windows.net:6380/0
```

Note in [flow.dag.yaml](flow.dag.yaml) we are using connection named `aoai_connection` for Azure Open AI and `redis_connection_url` for redis.

```bash
# show registered connection
pf connection show --name open_ai_connection
```

Please refer to connections [document](https://promptflow.azurewebsites.net/community/local/manage-connections.html) and [example](https://github.com/microsoft/promptflow/tree/main/examples/connections) for more details.

## Develop a chat flow

The most important elements that differentiate a chat flow from a standard flow are **Chat Input**, **Chat History**, and **Chat Output**.

- **Chat Input**: Chat input refers to the messages or queries submitted by users to the chatbot. Effectively handling chat input is crucial for a successful conversation, as it involves understanding user intentions, extracting relevant information, and triggering appropriate responses.

- **Chat History**: Chat history is the record of all interactions between the user and the chatbot, including both user inputs and AI-generated outputs. Maintaining chat history is essential for keeping track of the conversation context and ensuring the AI can generate contextually relevant responses. Chat History is a special type of chat flow input, that stores chat messages in a structured format.

  - NOTE: Currently the sample flows do not send chat history messages to agent workflow.

- **Chat Output**: Chat output refers to the AI-generated messages that are sent to the user in response to their inputs. Generating contextually appropriate and engaging chat outputs is vital for a positive user experience.

A chat flow can have multiple inputs, but Chat History and Chat Input are required inputs in chat flow.

## Interact with chat flow

Promptflow supports interacting via vscode or via Promptflow CLI provides a way to start an interactive chat session for chat flow. Customer can use below command to start an interactive chat session:

```bash
pf flow test --flow <flow_folder> --interactive
```

## Autogen State Flow

[Autogen State Flow](./autogen_stateflow.py) contains stateflow example shared at [StateFlow](https://microsoft.github.io/autogen/blog/2024/02/29/StateFlow/) with Promptflow. All the interim messages are sent to Redis channel. You can use these to stream to frontend or take further actions. Output of Prompflow is `summary` message from group chat.

## Agent Nested Chat

[Autogen Nested Chat](./agentchat_nestedchat.py) contains Scenario 1 of nested chat example shared at [Nested Chats](https://microsoft.github.io/autogen/docs/notebooks/agentchat_nestedchat) with Promptflow. All the interim messages are sent to Redis channel. You can use these to stream to frontend or take further actions. Output of Prompflow is `summary` message from group chat.

## Redis for Data cache and Interim Messages

Autogen supports Redis for [data caching](https://microsoft.github.io/autogen/docs/reference/cache/redis_cache/) and since redis supports a pub-subs model as well, this Promptflow example is configured for all agent callbacks to send messages to a Redis channel. This is optional feature but is essential for long running workflows and provides access to interim messages for your frontend. NOTE: Currently Promtpflow only support [SSE](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events) for streaming data and does not support websockets. NOTE: In multi user chat bot environment please make necessary changes to send messages to corresponding channel.
