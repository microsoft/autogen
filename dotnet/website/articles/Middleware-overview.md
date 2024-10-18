`Middleware` is a key feature in AutoGen.Net that enables you to customize the behavior of @AutoGen.Core.IAgent.GenerateReplyAsync*. It's similar to the middleware concept in ASP.Net and is widely used in AutoGen.Net for various scenarios, such as function call support, converting message of different types, print message, gather user input, etc.

Here are a few examples of how middleware is used in AutoGen.Net:
- @AutoGen.AssistantAgent is essentially an agent with @AutoGen.Core.FunctionCallMiddleware, @AutoGen.HumanInputMiddleware and default reply middleware.
- @AutoGen.OpenAI.GPTAgent is essentially an @AutoGen.OpenAI.OpenAIChatAgent with @AutoGen.Core.FunctionCallMiddleware and @AutoGen.OpenAI.OpenAIChatRequestMessageConnector.

## Use middleware in an agent
To use middleware in an existing agent, you can either create a @AutoGen.Core.MiddlewareAgent on top of the original agent or register middleware functions to the original agent.

### Create @AutoGen.Core.MiddlewareAgent on top of the original agent
[!code-csharp[](../../samples/AutoGen.BasicSamples/CodeSnippet/MiddlewareAgentCodeSnippet.cs?name=create_middleware_agent_with_original_agent)]

### Register middleware functions to the original agent
[!code-csharp[](../../samples/AutoGen.BasicSamples/CodeSnippet/MiddlewareAgentCodeSnippet.cs?name=register_middleware_agent)]

## Short-circuit the next agent
The example below shows how to short-circuit the inner agent

[!code-csharp[](../../samples/AutoGen.BasicSamples/CodeSnippet/MiddlewareAgentCodeSnippet.cs?name=short_circuit_middleware_agent)]

> [!Note]
> When multiple middleware functions are registered, the order of middleware functions is first registered, last invoked.

## Streaming middleware
You can also modify the behavior of @AutoGen.Core.IStreamingAgent.GenerateStreamingReplyAsync* by registering streaming middleware to it. One example is @AutoGen.OpenAI.OpenAIChatRequestMessageConnector which converts `StreamingChatCompletionsUpdate` to one of `AutoGen.Core.TextMessageUpdate` or `AutoGen.Core.ToolCallMessageUpdate`.

[!code-csharp[](../../samples/AutoGen.BasicSamples/CodeSnippet/MiddlewareAgentCodeSnippet.cs?name=register_streaming_middleware)]