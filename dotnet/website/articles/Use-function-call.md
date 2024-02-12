## Use function call in AutoGen agent
AutoGen supports function call in its built-in agent: @AutoGen.AssistantAgent and @AutoGen.UserProxyAgent. To use function call, simply use a model that support function call (e.g. `gpt-3.5-turbo-0613`), and pass `FunctionDefinition` when creating the agent. When the agent receives a message, it will intelligently decide whether to use function call or not based on the message received.
[!code-csharp[assistant agent](../../sample/AutoGen.BasicSamples/CodeSnippet/FunctionCallCodeSnippet.cs?name=code_snippet_4)]

## Invoke function call inside an agent
To invoke a function instead of returning the function call object, you can pass its function call wrapper to the agent via `functionMap`.

You can then pass the `WeatherReportWrapper` to the agent via `functionMap`:
[!code-csharp[](../../sample/AutoGen.BasicSamples/CodeSnippet/FunctionCallCodeSnippet.cs?name=code_snippet_6)]

When a function call object is returned, the agent will invoke the function and uses the return value as response rather than returning the function call object.

[!code-csharp[](../../sample/AutoGen.BasicSamples/CodeSnippet/FunctionCallCodeSnippet.cs?name=code_snippet_6_1)]

## Invoke function call by another agent
You can also use another agent to invoke the function call from one agent. This is a useful pattern in two-agent chat, where one agent is used as a function proxy to invoke the function call from another agent. Once the function call is invoked, the result can be returned to the original agent for further processing.

[!code-csharp[](../../sample/AutoGen.BasicSamples/CodeSnippet/FunctionCallCodeSnippet.cs?name=two_agent_weather_chat)]