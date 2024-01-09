@AutoGen.AgentExtension.RegisterPreProcess* enables you to apply an additional preprocessing logic over conversation context before the context is passed to the agent. This feature is useful when you want to modify the context for some situation, like retrieving and adding additional information or compress context.

> [!NOTE]
> @AutoGen.AgentExtension.RegisterPreProcess* will create an @AutoGen.PreProcessAgent on top of the original agent. The new agent will have the same name as the original agent. The original agent will remain unchanged.

[!code-csharp[](../../sample/AutoGen.BasicSamples/CodeSnippet/RegisterPreprocessCodeSnippet.cs?name=code_snippet_1)]

## The invoke order when multiple preprocess functions are registered

When multiple preprocess functions are registered, the order of preprocess functions is first registered, last invoked. For example, if you register preprocess functions A, B and C in order, then when a message is received, the order of preprocess functions being invoked is C, B and A.

[!code-csharp[](../../sample/AutoGen.BasicSamples/CodeSnippet/RegisterPreprocessCodeSnippet.cs?name=code_snippet_2)]
