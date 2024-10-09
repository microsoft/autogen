The following example shows how to create a `MistralAITokenCounterMiddleware` @AutoGen.Core.IMiddleware and count the token usage when chatting with @AutoGen.Mistral.MistralClientAgent.

### Overview
To collect the token usage for the entire chat session, one easy solution is simply collect all the responses from agent and sum up the token usage for each response. To collect all the agent responses, we can create a middleware which simply saves all responses to a list and register it with the agent. To get the token usage information for each response, because in the example we are using @AutoGen.Mistral.MistralClientAgent, we can simply get the token usage from the response object.

> [!NOTE]
> You can find the complete example in the [Example13_OpenAIAgent_JsonMode](https://github.com/microsoft/autogen/tree/main/dotnet/samples/AutoGen.BasicSamples/Example14_MistralClientAgent_TokenCount.cs).

- Step 1: Adding using statement
[!code-csharp[](../../samples/AutoGen.BasicSamples/Example14_MistralClientAgent_TokenCount.cs?name=using_statements)]

- Step 2: Create a `MistralAITokenCounterMiddleware` class which implements @AutoGen.Core.IMiddleware. This middleware will collect all the responses from the agent and sum up the token usage for each response.
[!code-csharp[](../../samples/AutoGen.BasicSamples/Example14_MistralClientAgent_TokenCount.cs?name=token_counter_middleware)]

- Step 3: Create a `MistralClientAgent`
[!code-csharp[](../../samples/AutoGen.BasicSamples/Example14_MistralClientAgent_TokenCount.cs?name=create_mistral_client_agent)]

- Step 4: Register the `MistralAITokenCounterMiddleware` with the `MistralClientAgent`. Note that the order of each middlewares matters. The token counter middleware needs to be registered before `mistralMessageConnector` because it collects response only when the responding message type is `IMessage<ChatCompletionResponse>` while the `mistralMessageConnector` will convert `IMessage<ChatCompletionResponse>` to one of @AutoGen.Core.TextMessage, @AutoGen.Core.ToolCallMessage or @AutoGen.Core.ToolCallResultMessage.
[!code-csharp[](../../samples/AutoGen.BasicSamples/Example14_MistralClientAgent_TokenCount.cs?name=register_middleware)]

- Step 5: Chat with the `MistralClientAgent` and get the token usage information from the response object.
[!code-csharp[](../../samples/AutoGen.BasicSamples/Example14_MistralClientAgent_TokenCount.cs?name=chat_with_agent)]

### Output
When running the example, the completion token count will be printed to the console.
```bash
Completion token count: 1408 # might be different based on the response
```