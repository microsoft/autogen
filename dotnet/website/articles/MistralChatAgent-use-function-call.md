## Use tool in MistralChatAgent

The following example shows how to enable tool support in @AutoGen.Mistral.MistralClientAgent by creating a `GetWeatherAsync` function and passing it to the agent.

Firstly, you need to install the following packages:
```bash
dotnet add package AutoGen.Mistral
dotnet add package AutoGen.SourceGenerator
```

> [!Note]
> Tool support is only available in some mistral models. Please refer to the [link](https://docs.mistral.ai/capabilities/function_calling/#available-models) for tool call support in mistral models.

> [!Note]
> The `AutoGen.SourceGenerator` package carries a source generator that adds support for type-safe function definition generation. For more information, please check out [Create type-safe function](./Create-type-safe-function-call.md).

> [!NOTE]
> If you are using VSCode as your editor, you may need to restart the editor to see the generated code.

Import the required namespace
[!code-csharp[](../../samples/AgentChat/Autogen.Basic.Sample/CodeSnippet/MistralAICodeSnippet.cs?name=using_statement)]

Then define a public partial `MistralAgentFunction` class and `GetWeather` method. The `GetWeather` method is a simple function that returns the weather of a given location that marked with @AutoGen.Core.FunctionAttribute. Marking the class as `public partial` together with the @AutoGen.Core.FunctionAttribute attribute allows the source generator to generate the @AutoGen.Core.FunctionContract for the `GetWeather` method.

[!code-csharp[](../../samples/AgentChat/Autogen.Basic.Sample/CodeSnippet/MistralAICodeSnippet.cs?name=weather_function)]

Then create an @AutoGen.Mistral.MistralClientAgent and register it with @AutoGen.Mistral.Extension.MistralAgentExtension.RegisterMessageConnector* so it can support @AutoGen.Core.ToolCallMessage and @AutoGen.Core.ToolCallResultMessage. These message types are necessary to use @AutoGen.Core.FunctionCallMiddleware, which provides support for processing and invoking function calls.

[!code-csharp[](../../samples/AgentChat/Autogen.Basic.Sample/CodeSnippet/MistralAICodeSnippet.cs?name=create_mistral_function_call_agent)]

Then create an @AutoGen.Core.FunctionCallMiddleware with `GetWeather` function When creating the middleware, we also pass a `functionMap` object which means the function will be automatically invoked when the agent replies a `GetWeather` function call.

[!code-csharp[](../../samples/AgentChat/Autogen.Basic.Sample/CodeSnippet/MistralAICodeSnippet.cs?name=create_get_weather_function_call_middleware)]

After the function call middleware is created, register it with the agent so the `GetWeather` function will be passed to agent during chat completion.

[!code-csharp[](../../samples/AgentChat/Autogen.Basic.Sample/CodeSnippet/MistralAICodeSnippet.cs?name=register_function_call_middleware)]

Finally, you can chat with the @AutoGen.Mistral.MistralClientAgent about weather! The agent will automatically invoke the `GetWeather` function to "get" the weather information and return the result.

[!code-csharp[](../../samples/AgentChat/Autogen.Basic.Sample/CodeSnippet/MistralAICodeSnippet.cs?name=send_message_with_function_call)]