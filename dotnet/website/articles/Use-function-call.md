## What's Function call

Function call is a feature in some LLM models that returns a function call json object which can be used to invoke a function. To use a function call, one or several function definitions need to be provided to the model. The model will then use the function definitions to generate function call json object.

Currently, GPT chat models with version later than `0613` support function call. For more information, please check out [OpenAI API documentation](https://platform.openai.com/docs/guides/function-calling).

## Use function call in AutoGen agent
AutoGen supports function call in [`AssistantAgent`](../api/AutoGen.AssistantAgent.yml), [`UserProxyAgent`](../api/AutoGen.UserProxyAgent.yml) and [`GPTAgent`](../api/AutoGen.OpenAI.GPTAgent.yml). To use function call, simply use a model that support function call (e.g. `gpt-3.5-turbo-0613`), and pass `FunctionDefinition` when creating the agent.

Suppose that you want to invoke the following function in your agent:

[!code-csharp[](../../sample/AutoGen.BasicSamples/CodeSnippet/FunctionCallCodeSnippet.cs?name=code_snippet_3)]

Firstly, you need to create a function definition to represent the function. The function definition is essentially an OpenAPI schema object which describes the function, its parameters and return value. When passing to LLM model, the function definition will be used to generate function call json object.

[!code-csharp[](../../sample/AutoGen.BasicSamples/CodeSnippet/FunctionCallCodeSnippet.cs?name=code_snippet_1)]

> [!TIP]
> You can use [`Function`](../api/AutoGen.FunctionAttribute.yml) to generate type-safe function definition and function call wrapper for the function. For more information, please check out [Create type safe function call](./Create-type-safe-function-call.md).

Then, pass the function definition to the agent when creating it.

[!code-csharp[assistant agent](../../sample/AutoGen.BasicSamples/CodeSnippet/FunctionCallCodeSnippet.cs?name=code_snippet_4)]

[!code-csharp[gpt agent](../../sample/AutoGen.BasicSamples/CodeSnippet/FunctionCallCodeSnippet.cs?name=code_snippet_5)]

When the agent receives a message, it will intelligently decide whether to use function call or not based on the message received.

[!code-csharp[gpt agent](../../sample/AutoGen.BasicSamples/CodeSnippet/FunctionCallCodeSnippet.cs?name=code_snippet_5_1)]

The following function call object will be generated, which can be used to invoke the actual function.

(raw function call object)
```json
{
    "function_name": "UpperCase",
    "function_arguments": {
        "text": "hello world"
    }
}
```

[!code-csharp[gpt agent](../../sample/AutoGen.BasicSamples/CodeSnippet/FunctionCallCodeSnippet.cs?name=code_snippet_5_2)]

## Invoke function call

To invoke a function instead of returning the function call object, you can pass its function call wrapper to the agent via `functionMap`.

Suppose the following function call wrapper `UpperCaseWrapper` is given:
[!code-csharp[](../../sample/AutoGen.BasicSamples/CodeSnippet/FunctionCallCodeSnippet.cs?name=code_snippet_2)]

You can then pass the `UpperCaseWrapper` to the agent via `functionMap`:
[!code-csharp[](../../sample/AutoGen.BasicSamples/CodeSnippet/FunctionCallCodeSnippet.cs?name=code_snippet_6)]

When a function call object is returned, the agent will invoke the function and uses the return value as response rather than returning the function call object.

[!code-csharp[](../../sample/AutoGen.BasicSamples/CodeSnippet/FunctionCallCodeSnippet.cs?name=code_snippet_6_1)]
