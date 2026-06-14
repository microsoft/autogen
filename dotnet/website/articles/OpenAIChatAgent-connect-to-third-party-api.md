The following example shows how to connect to third-party OpenAI API using @AutoGen.OpenAI.OpenAIChatAgent.

[![](https://img.shields.io/badge/Open%20on%20Github-grey?logo=github)](https://github.com/microsoft/autogen/blob/main/dotnet/samples/AgentChat/AutoGen.OpenAI.Sample/Connect_To_Tuning_Engines.cs)

## Overview
A lot of LLM applications/platforms support spinning up a chat server that is compatible with OpenAI API, such as LM Studio, Ollama, Mistral etc. This means that you can connect to these servers using the @AutoGen.OpenAI.OpenAIChatAgent.

You can also connect to a governed OpenAI-compatible endpoint when your organization wants AutoGen to own the agent workflow while a centralized control plane handles model access, policy, audit trails, quotas, routing, and cost reporting. For example, [Tuning Engines](https://www.tuningengines.com/) exposes an OpenAI-compatible inference endpoint that can be configured with `OpenAIClientOptions.Endpoint`.

> [!NOTE]
> Some platforms might not support all the features of OpenAI API. For example, Ollama does not support `function call` when using it's openai API according to its [document](https://github.com/ollama/ollama/blob/main/docs/openai.md#v1chatcompletions) (as of 2024/05/07).
> That means some of the features of OpenAI API might not work as expected when using these platforms with the @AutoGen.OpenAI.OpenAIChatAgent.
> Please refer to the platform's documentation for more information.

## Prerequisites
- Install the following packages:
```bash
dotnet add package AutoGen.OpenAI --version AUTOGEN_VERSION
```

- Spin up a chat server that is compatible with OpenAI API.
The following example uses Ollama as the chat server, and llama3 as the llm model.
```bash
ollama serve
```

## Steps
- Import the required namespaces:
[!code-csharp[](../../samples/AgentChat/AutoGen.OpenAI.Sample/Connect_To_Ollama.cs?name=using_statement)]

- Create an `OpenAIChatAgent` instance and connect to the third-party API.

Then create an @AutoGen.OpenAI.OpenAIChatAgent instance and connect to the OpenAI API from Ollama. You can customize the endpoint by passing `OpenAIClientOptions` to `OpenAIClient`.

[!code-csharp[](../../samples/AgentChat/AutoGen.OpenAI.Sample/Connect_To_Ollama.cs?name=create_agent)]

For a governed OpenAI-compatible endpoint such as Tuning Engines, set `TUNING_ENGINES_API_KEY` and optionally `TUNING_ENGINES_MODEL`, then point the OpenAI client at the gateway endpoint:

[!code-csharp[](../../samples/AgentChat/AutoGen.OpenAI.Sample/Connect_To_Tuning_Engines.cs?name=create_agent)]

- Chat with the `OpenAIChatAgent`.
Finally, you can start chatting with the agent. In this example, we send a coding question to the agent and get the response.

[!code-csharp[](../../samples/AgentChat/AutoGen.OpenAI.Sample/Connect_To_Tuning_Engines.cs?name=send_message)]

## Sample Output
The following is the sample output of the code snippet above:

![output](../images/articles/ConnectTo3PartyOpenAI/output.gif)
