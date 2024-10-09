## Use function call in AutoGen agent

Typically, there are three ways to pass a function definition to an agent to enable function call:
- Pass function definitions when creating an agent. This only works if the agent supports pass function call from its constructor.
- Passing function definitions in @AutoGen.Core.GenerateReplyOptions when invoking an agent
- Register an agent with @AutoGen.Core.FunctionCallMiddleware to process and invoke function calls.

> [!NOTE]
> To use function call, the underlying LLM model must support function call as well for the best experience. If the model does not support function call, it's likely that the function call will be ignored and the model will reply with a normal response even if a function call is passed to it.

## Pass function definitions when creating an agent
In some agents like @AutoGen.AssistantAgent or @AutoGen.OpenAI.GPTAgent, you can pass function definitions when creating the agent

Suppose the `TypeSafeFunctionCall` is defined in the following code snippet:
[!code-csharp[TypeSafeFunctionCall](../../samples/AutoGen.BasicSamples/CodeSnippet/TypeSafeFunctionCallCodeSnippet.cs?name=weather_report)]

You can then pass the `WeatherReport` to the agent when creating it:
[!code-csharp[assistant agent](../../samples/AutoGen.BasicSamples/CodeSnippet/FunctionCallCodeSnippet.cs?name=code_snippet_4)]

## Passing function definitions in @AutoGen.Core.GenerateReplyOptions when invoking an agent
You can also pass function definitions in @AutoGen.Core.GenerateReplyOptions when invoking an agent. This is useful when you want to override the function definitions passed to the agent when creating it.

[!code-csharp[assistant agent](../../samples/AutoGen.BasicSamples/CodeSnippet/FunctionCallCodeSnippet.cs?name=overrider_function_contract)]

## Register an agent with @AutoGen.Core.FunctionCallMiddleware to process and invoke function calls
You can also register an agent with @AutoGen.Core.FunctionCallMiddleware to process and invoke function calls. This is useful when you want to process and invoke function calls in a more flexible way.

[!code-csharp[assistant agent](../../samples/AutoGen.BasicSamples/CodeSnippet/FunctionCallCodeSnippet.cs?name=register_function_call_middleware)]

## Invoke function call inside an agent
To invoke a function instead of returning the function call object, you can pass its function call wrapper to the agent via `functionMap`.

You can then pass the `WeatherReportWrapper` to the agent via `functionMap`:
[!code-csharp[](../../samples/AutoGen.BasicSamples/CodeSnippet/FunctionCallCodeSnippet.cs?name=code_snippet_6)]

When a function call object is returned, the agent will invoke the function and uses the return value as response rather than returning the function call object.

[!code-csharp[](../../samples/AutoGen.BasicSamples/CodeSnippet/FunctionCallCodeSnippet.cs?name=code_snippet_6_1)]

## Invoke function call by another agent
You can also use another agent to invoke the function call from one agent. This is a useful pattern in two-agent chat, where one agent is used as a function proxy to invoke the function call from another agent. Once the function call is invoked, the result can be returned to the original agent for further processing.

[!code-csharp[](../../samples/AutoGen.BasicSamples/CodeSnippet/FunctionCallCodeSnippet.cs?name=two_agent_weather_chat)]