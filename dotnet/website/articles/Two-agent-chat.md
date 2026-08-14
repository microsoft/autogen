In `AutoGen`, you can start a conversation between two agents using @AutoGen.Core.AgentExtension.InitiateChatAsync* or one of @AutoGen.Core.AgentExtension.SendAsync* APIs. When conversation starts, the sender agent will firstly send a message to receiver agent, then receiver agent will generate a reply and send it back to sender agent. This process will repeat until either one of the agent sends a termination message or the maximum number of turns is reached.

> [!NOTE]
> A termination message is an @AutoGen.Core.IMessage which content contains the keyword: @AutoGen.Core.GroupChatExtension.TERMINATE. To determine if a message is a terminate message, you can use @AutoGen.Core.GroupChatExtension.IsGroupChatTerminateMessage*.

## A basic example

The following example shows how to start a conversation between the teacher agent and student agent, where the student agent starts the conversation by asking teacher to create math questions.

> [!TIP]
> You can use @AutoGen.Core.PrintMessageMiddlewareExtension.RegisterPrintMessage* to pretty print the message replied by the agent.

> [!NOTE]
> The conversation is terminated when teacher agent sends a message containing the keyword: @AutoGen.Core.GroupChatExtension.TERMINATE.

> [!NOTE]
> The teacher agent uses @AutoGen.Core.MiddlewareExtension.RegisterPostProcess* to register a post process function which returns a hard-coded termination message when a certain condition is met. Comparing with putting the @AutoGen.Core.GroupChatExtension.TERMINATE keyword in the prompt, this approach is more robust especially when a weaker LLM model is used.

[!code-csharp[](../../samples/AgentChat/Autogen.Basic.Sample/Example02_TwoAgent_MathChat.cs?name=code_snippet_1)]
