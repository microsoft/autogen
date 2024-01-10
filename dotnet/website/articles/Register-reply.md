@AutoGen.AgentExtension.RegisterReply* enables you to customize an agent's behavior by registering a reply function on top of the agent. The reply function will be called before the original agent's reply function. If the reply function returns a non-null value, the original agent's reply function will not be called. Otherwise, the original agent's reply function will be invoked.

> [!NOTE]
> @AutoGen.AgentExtension.RegisterReply* will create an @AutoGen.AutoReplyAgent on top of the original agent. The new agent will have the same name as the original agent. The original agent will remain unchanged.

This feature is useful when you want to create an agent that has the same behavior as the original agent, but with some additional logic. For example, the @AutoGen.DotnetInteractive.AgentExtension.RegisterDotnetCodeBlockExectionHook* adds the logic of detecting and running dotnet code snippet so that when a dotnet code snippet is present in the most recent message from history, dotnet interactive will be invoked to run the code snippet and the result will be returned as the agent's reply.

[!code-csharp[](../../sample/AutoGen.BasicSamples/CodeSnippet/RunCodeSnippetCodeSnippet.cs?name=code_snippet_1_2)]

## The invoke order when multiple reply functions are registered

When multiple reply functions are registered, the order of reply functions is first registered, last invoked. For example, if you register reply functions A, B and C in order, then when a message is received, the order of reply functions being invoked is C, B and A.

> [!NOTE]
> The order of reply functions is first registered, last invoked.

[!code-csharp[](../../sample/AutoGen.BasicSamples/CodeSnippet/RegisterReplyCodeSnippet.cs?name=code_snippet_1)]

