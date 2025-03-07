// Copyright (c) Microsoft Corporation. All rights reserved.
// ChatAgentRouter.cs

using Microsoft.AutoGen.AgentChat.Abstractions;
using Microsoft.AutoGen.Contracts;
using Microsoft.AutoGen.Core;
using Microsoft.Extensions.Logging;

namespace Microsoft.AutoGen.AgentChat.GroupChat;

public struct AgentChatConfig(IChatAgent chatAgent, string parentTopicType, string outputTopicType)
{
    public string ParticipantTopicType => this.Name;
    public string ParentTopicType { get; } = parentTopicType;
    public string OutputTopicType { get; } = outputTopicType;

    public IChatAgent ChatAgent { get; } = chatAgent;

    public string Name => this.ChatAgent.Name;
    public string Description => this.ChatAgent.Description;
}

internal sealed class ChatAgentRouter : HostableAgentAdapter,
                                        IHandle<GroupChatStart>,
                                        IHandle<GroupChatAgentResponse>,
                                        IHandle<GroupChatRequestPublish>,
                                        IHandle<GroupChatReset>
{
    private readonly TopicId parentTopic;
    private readonly TopicId outputTopic;
    private readonly IChatAgent agent;

    public ChatAgentRouter(AgentInstantiationContext agentCtx, AgentChatConfig config, ILogger<BaseAgent>? logger = null) : base(agentCtx, config.Description, logger)
    {
        this.parentTopic = new TopicId(config.ParentTopicType, this.Id.Key);
        this.outputTopic = new TopicId(config.OutputTopicType, this.Id.Key);

        this.agent = config.ChatAgent;
    }

    public List<ChatMessage> MessageBuffer { get; private set; } = new();

    public ValueTask HandleAsync(GroupChatStart item, MessageContext messageContext)
    {
        if (item.Messages != null)
        {
            this.MessageBuffer.AddRange(item.Messages);
        }

        return ValueTask.CompletedTask;
    }

    public ValueTask HandleAsync(GroupChatAgentResponse item, MessageContext messageContext)
    {
        this.MessageBuffer.Add(item.AgentResponse.Message);

        return ValueTask.CompletedTask;
    }

    public async ValueTask HandleAsync(GroupChatRequestPublish item, MessageContext messageContext)
    {
        Response? response = null;

        // TODO: Is there a better abstraction here than IAsyncEnumerable? Though the akwardness mainly comes from
        // the lack of real type unions in C#, which is why we need to create the StreamingFrame type in the first
        // place.
        await foreach (ChatStreamFrame frame in this.agent.StreamAsync(this.MessageBuffer, messageContext.CancellationToken))
        {
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

        this.MessageBuffer.Clear();

        await this.PublishMessageAsync(new GroupChatAgentResponse { AgentResponse = response }, this.parentTopic);
    }

    public ValueTask HandleAsync(GroupChatReset item, MessageContext messageContext)
    {
        this.MessageBuffer.Clear();
        return this.agent.ResetAsync(messageContext.CancellationToken);
    }
}

