The following example shows how to create a `GetWeatherAsync` function and pass it to @AutoGen.OpenAI.OpenAIChatAgent.

Firstly, you need to install the following packages:
```xml
<ItemGroup>
    <PackageReference Include="AutoGen.OpenAI" Version="AUTOGEN_VERSION" />
    <PackageReference Include="AutoGen.SourceGenerator" Version="AUTOGEN_VERSION" />
</ItemGroup>
```

> [!Note]
> The `AutoGen.SourceGenerator` package carries a source generator that adds support for type-safe function definition generation. For more information, please check out [Create type-safe function](./Create-type-safe-function-call.md).

> [!NOTE]
> If you are using VSCode as your editor, you may need to restart the editor to see the generated code.

Firstly, import the required namespaces:
[!code-csharp[](../../samples/AutoGen.BasicSamples/CodeSnippet/OpenAICodeSnippet.cs?name=using_statement)]

Then, define a public partial class: `Function` with `GetWeather` method
[!code-csharp[](../../samples/AutoGen.BasicSamples/CodeSnippet/OpenAICodeSnippet.cs?name=weather_function)]

Then, create an @AutoGen.OpenAI.OpenAIChatAgent and register it with @AutoGen.OpenAI.OpenAIChatRequestMessageConnector so it can support @AutoGen.Core.ToolCallMessage and @AutoGen.Core.ToolCallResultMessage. These message types are necessary to use @AutoGen.Core.FunctionCallMiddleware, which provides support for processing and invoking function calls.

[!code-csharp[](../../samples/AutoGen.BasicSamples/CodeSnippet/OpenAICodeSnippet.cs?name=openai_chat_agent_get_weather_function_call)]

Then, create an @AutoGen.Core.FunctionCallMiddleware with `GetWeather` function and register it with the agent above. When creating the middleware, we also pass a `functionMap` to @AutoGen.Core.FunctionCallMiddleware, which means the function will be automatically invoked when the agent replies a `GetWeather` function call.

[!code-csharp[](../../samples/AutoGen.BasicSamples/CodeSnippet/OpenAICodeSnippet.cs?name=create_function_call_middleware)]

Finally, you can chat with the @AutoGen.OpenAI.OpenAIChatAgent and invoke the `GetWeather` function.

[!code-csharp[](../../samples/AutoGen.BasicSamples/CodeSnippet/OpenAICodeSnippet.cs?name=chat_agent_send_function_call)]