## AssistantAgent

[`AssistantAgent`](../api/AutoGen.AssistantAgent.yml) is a built-in agent in `AutoGen` that acts as an AI assistant. It uses LLM to generate response to user input. It also supports function call if the underlying LLM model supports it (e.g. `gpt-3.5-turbo-0613`).

## Create an `AssistantAgent` using OpenAI model.

[!code-csharp[](../../sample/AutoGen.BasicSamples/CodeSnippet/CreateAnAgent.cs?name=code_snippet_1)]

## Create an `AssistantAgent` using Azure OpenAI model.

[!code-csharp[](../../sample/AutoGen.BasicSamples/CodeSnippet/CreateAnAgent.cs?name=code_snippet_2)]

## Function call

To use function call, simply use a model that support function call (e.g. `gpt-3.5-turbo-0613`), and pass `FunctionDefinition` when creating the agent.

Firstly, define the function object using [`Function`](../api/AutoGen.FunctionAttribute.yml) attribute. The `Function` attribute tells `AutoGen.SourceGenerator` to generate a function definition and function call wrapper for the function.
[!code-csharp[](../../sample/AutoGen.BasicSamples/CodeSnippet/CreateAnAgent.cs?name=code_snippet_3)]

> Note: You need to add the `AutoGen.SourceGenerator` package to your project to use this feature.

Then, pass the function definition to the agent when creating it.
[!code-csharp[](../../sample/AutoGen.BasicSamples/CodeSnippet/CreateAnAgent.cs?name=code_snippet_4)]

To execute the function instead of returning the function call object, you can pass its function call wrapper to the agent via `functionMap`

[!code-csharp[](../../sample/AutoGen.BasicSamples/CodeSnippet/CreateAnAgent.cs?name=code_snippet_5)]