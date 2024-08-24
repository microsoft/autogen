`Agent` is one of the most fundamental concepts in AutoGen.Net. In AutoGen.Net, you construct a single agent to process a specific task, and you extend an agent using [Middlewares](./Middleware-overview.md), and you construct a multi-agent workflow using [GroupChat](./Group-chat-overview.md).

> [!NOTE]
> Every agent in AutoGen.Net implements @AutoGen.Core.IAgent, for agent that supports streaming reply, it also implements @AutoGen.Core.IStreamingAgent.

## Create an agent
- Create an @AutoGen.AssistantAgent: [Create an assistant agent](./Create-an-agent.md)
- Create an @AutoGen.OpenAI.OpenAIChatAgent: [Create an OpenAI chat agent](./OpenAIChatAgent-simple-chat.md)
- Create a @AutoGen.SemanticKernel.SemanticKernelAgent: [Create a semantic kernel agent](./AutoGen.SemanticKernel/SemanticKernelAgent-simple-chat.md)
- Create a @AutoGen.LMStudio.LMStudioAgent: [Connect to LM Studio](./Consume-LLM-server-from-LM-Studio.md)

## Chat with an agent
To chat with an agent, typically you can invoke @AutoGen.Core.IAgent.GenerateReplyAsync*. On top of that, you can also use one of the extension methods like @AutoGen.Core.AgentExtension.SendAsync* as shortcuts.

> [!NOTE]
> AutoGen provides a list of built-in message types like @AutoGen.Core.TextMessage, @AutoGen.Core.ImageMessage, @AutoGen.Core.MultiModalMessage, @AutoGen.Core.ToolCallMessage, @AutoGen.Core.ToolCallResultMessage, etc. You can use these message types to chat with an agent. For further details, see [built-in messages](./Built-in-messages.md).

- Send a @AutoGen.Core.TextMessage to an agent via @AutoGen.Core.IAgent.GenerateReplyAsync*:
[!code-csharp[](../../sample/AutoGen.BasicSamples/CodeSnippet/AgentCodeSnippet.cs?name=ChatWithAnAgent_GenerateReplyAsync)]

- Send a message to an agent via @AutoGen.Core.AgentExtension.SendAsync*:
[!code-csharp[](../../sample/AutoGen.BasicSamples/CodeSnippet/AgentCodeSnippet.cs?name=ChatWithAnAgent_SendAsync)]

## Streaming chat
If an agent implements @AutoGen.Core.IStreamingAgent, you can use @AutoGen.Core.IStreamingAgent.GenerateStreamingReplyAsync* to chat with the agent in a streaming way. You would need to process the streaming updates on your side though.

- Send a @AutoGen.Core.TextMessage to an agent via @AutoGen.Core.IStreamingAgent.GenerateStreamingReplyAsync*, and print the streaming updates to console:
[!code-csharp[](../../sample/AutoGen.BasicSamples/CodeSnippet/AgentCodeSnippet.cs?name=ChatWithAnAgent_GenerateStreamingReplyAsync)]

## Register middleware to an agent
@AutoGen.Core.IMiddleware and @AutoGen.Core.IStreamingMiddleware are used to extend the behavior of @AutoGen.Core.IAgent.GenerateReplyAsync* and @AutoGen.Core.IStreamingAgent.GenerateStreamingReplyAsync*. You can register middleware to an agent to customize the behavior of the agent on things like function call support, converting message of different types, print message, gather user input, etc.

- Middleware overview: [Middleware overview](./Middleware-overview.md)
- Write message to console: [Print message middleware](./Print-message-middleware.md)
- Convert message type: [SemanticKernelChatMessageContentConnector](./AutoGen.SemanticKernel/SemanticKernelAgent-support-more-messages.md) and [OpenAIChatRequestMessageConnector](./OpenAIChatAgent-support-more-messages.md)
- Create your own middleware: [Create your own middleware](./Create-your-own-middleware.md)

## Group chat
You can construct a multi-agent workflow using @AutoGen.Core.IGroupChat. In AutoGen.Net, there are two type of group chat:
@AutoGen.Core.SequentialGroupChat: Orchestrates the agents in the group chat in a fix, sequential order.
@AutoGen.Core.GroupChat: Provide more dynamic yet controllable way to orchestrate the agents in the group chat.

For further details, see [Group chat overview](./Group-chat-overview.md).