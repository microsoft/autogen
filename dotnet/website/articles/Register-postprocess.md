@AutoGen.AgentExtension.RegisterPostProcess* enables you to apply an additional postprocessing logic once the agent generates a reply. The postprocessing function takes in both the conversation history and agent reply as input, and returns a new reply as output, which will be used as the final agent reply to the user.

> [!NOTE]
> @AutoGen.AgentExtension.RegisterPostProcess* will create an @AutoGen.PostProcessAgent on top of the original agent. The new agent will have the same name as the original agent. The original agent will remain unchanged.

This feature is useful when you want to modify the agent reply for some situation. For example, in `Example_4_Dynamic_GroupChat_Get_MLNET_PR`, we use this feature to perform sanity check over dotnet coder agent to make sure the code snippet from it is written in top-level statement. This feature is also useful for logging purpose. For example, `AutoGen` provides a built-in @AutoGen.AgentExtension.RegisterPrintFormatMessageHook* to print the reply message nicely in console.

[!code-csharp[](../../sample/AutoGen.BasicSamples/CodeSnippet/RegisterPostProcessCodeSnippet.cs?name=code_snippet_1)]

## The invoke order when multiple postprocess functions are registered

When multiple postprocess functions are registered, the order of postprocess functions is first registered, first invoked. For example, if you register postprocess functions A, B and C in order, then when a message is received, the order of postprocess functions being invoked is still A, B and C.

> [!NOTE]
> Unlike reply and preprocess functions, The order of postprocess functions is first registered, first invoked.

[!code-csharp[](../../sample/AutoGen.BasicSamples/CodeSnippet/RegisterPostProcessCodeSnippet.cs?name=code_snippet_2)]
