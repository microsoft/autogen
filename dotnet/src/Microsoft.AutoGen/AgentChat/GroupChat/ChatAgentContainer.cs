// Copyright (c) Microsoft Corporation. All rights reserved.
// ChatAgentContainer.cs

using Microsoft.AutoGen.Abstractions;
using Microsoft.AutoGen.AgentChat.Abstractions;
using Microsoft.AutoGen.Agents;

namespace Microsoft.AutoGen.AgentChat.GroupChat;

internal sealed class ChatAgentContainer : SequentialRoutedAgent,
                                    IHandleEx<GroupChatStart>,
                                    IHandleEx<GroupChatAgentResponse>,
                                    IHandleEx<GroupChatReset>,
                                    IHandleEx<GroupChatRequestPublish>,
                                    IHandleDefault
{
    private readonly string parentTopic;
    private readonly string outputTopic;
    private readonly IChatAgent agent;
    private readonly List<ChatMessage> messageBuffer;

    public ChatAgentContainer(IAgentRuntime agentContext, EventTypes eventTypes, AgentChatBinder configurator)
        : base(agentContext, eventTypes)
    {
        AgentChatConfig agentConfig = configurator[agentContext.AgentId.Key];

        this.agent = agentConfig.ChatAgent;
        this.parentTopic = agentConfig.ParentTopic;
        this.outputTopic = agentConfig.OutputTopic;

        configurator.SubscribeGroup(this);

        this.messageBuffer = new List<ChatMessage>();
    }

    public ValueTask HandleAsync(GroupChatStart item, CancellationToken cancellationToken)
    {
        if (item.Message != null)
        {
            this.messageBuffer.Add(item.Message);
        }

        return ValueTask.CompletedTask;
    }

    public ValueTask HandleAsync(GroupChatAgentResponse item, CancellationToken cancellationToken)
    {
        this.messageBuffer.Add(item.AgentResponse.Message);
        return ValueTask.CompletedTask;
    }

    public ValueTask HandleAsync(GroupChatReset item, CancellationToken cancellationToken)
    {
        this.messageBuffer.Clear();

        return this.agent.ResetAsync(cancellationToken);
    }

    public async ValueTask HandleAsync(GroupChatRequestPublish item, CancellationToken cancellationToken)
    {
        Response? response = null;

        // TODO: Is there a better abstraction here than IAsyncEnumerable? Though the akwardness mainly comes from
        // the lack of real type unions in C#, which is why we need to create the StreamingFrame type in the first
        // place.
        await foreach (ChatStreamFrame frame in this.agent.StreamAsync(this.messageBuffer, cancellationToken))
        {
            // TODO: call publish message
            switch (frame.Type)
            {
                case ChatStreamFrame.FrameType.Response:
                    await this.PublishMessageAsync(new GroupChatMessage { Message = frame.Response!.Message }, this.outputTopic);
                    response = frame.Response;
                    break;
                case ChatStreamFrame.FrameType.InternalMessage:
                    await this.PublishMessageAsync(new GroupChatMessage { Message = frame.InternalMessage! }, this.outputTopic);
                    break;
            }
        }

        if (response == null)
        {
            throw new InvalidOperationException("The agent did not produce a final response. Check the agent's on_messages_stream method.");
        }

        this.messageBuffer.Clear();
        await this.PublishMessageAsync(new GroupChatAgentResponse { AgentResponse = response }, this.parentTopic);
    }

    ValueTask IHandleEx<object>.HandleAsync(object item, CancellationToken cancellationToken)
    {
        throw new InvalidOperationException($"Unhandled message in agent container: {item.GetType()}");
    }
}
