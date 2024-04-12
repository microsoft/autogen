# Chat flow

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

- **Chat Output**: Chat output refers to the AI-generated messages that are sent to the user in response to their inputs. Generating contextually appropriate and engaging chat outputs is vital for a positive user experience.

A chat flow can have multiple inputs, but Chat History and Chat Input are required inputs in chat flow.

## Interact with chat flow

Promptflow CLI provides a way to start an interactive chat session for chat flow. Customer can use below command to start an interactive chat session:

```bash
pf flow test --flow <flow_folder> --interactive
```

## Autogen State Flow

This flow contains stateflow example shared at [StateFlow](https://microsoft.github.io/autogen/blog/2024/02/29/StateFlow/) with Promptflow. All the interim messages are stored in Redis. You can use these to stream to frontend or take further actions

## Autogen Nested Chat

This flow contains Scenario 1 of nested chat example shared at [Nested Chats](https://microsoft.github.io/autogen/docs/notebooks/agentchat_nestedchat) with Promptflow. All the interim messages are stored in Redis. You can use these to stream to frontend or take further actions
