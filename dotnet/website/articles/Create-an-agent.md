## AssistantAgent

[`AssistantAgent`](../api/AutoGen.AssistantAgent.yml) is a built-in agent in `AutoGen` that acts as an AI assistant. It uses LLM to generate response to user input. It also supports function call if the underlying LLM model supports it (e.g. `gpt-3.5-turbo-0613`).

## Create an `AssistantAgent` using OpenAI model.

[!code-csharp[](../../samples/AgentChat/Autogen.Basic.Sample/CodeSnippet/CreateAnAgent.cs?name=code_snippet_1)]

## Create an `AssistantAgent` using Azure OpenAI model.

[!code-csharp[](../../samples/AgentChat/Autogen.Basic.Sample/CodeSnippet/CreateAnAgent.cs?name=code_snippet_2)]
