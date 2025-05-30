// Copyright (c) Microsoft Corporation. All rights reserved.
// GroupChatManagerBase.cs

using Microsoft.AutoGen.AgentChat.Abstractions;
using Microsoft.AutoGen.Contracts;

namespace Microsoft.AutoGen.AgentChat.GroupChat;

public abstract class GroupChatManagerBase : IGroupChatHandler
{
    private GroupChatOptions options;

    // TODO: We may be able to abstract this out at the Core level
    private MessagePublishServicer? PublishServicer { get; set; }

    // It would be so awesome if we could avoid passing GroupChatOptions to the constructor
    // and use something like Python's context manager mechanism to pick up the options from
    // the logical stack. But that's very difficult in C#, because the user code could do all
    // sorts of weird things like shunt the execution to a different thread. We cannot even
    // assume that we are in an async context (much less that we are in the same async context)
    public GroupChatManagerBase(GroupChatOptions options) : base()
    {
        this.options = options;

        this.MessageThread = new List<AgentMessage>();
    }

    protected string GroupChatTopicType => this.options.GroupChatTopicType;
    protected string OutputTopicType => this.options.OutputTopicType;

    protected Dictionary<string, GroupParticipant> Participants => this.options.Participants;

    protected ITerminationCondition? TerminationCondition => this.options.TerminationCondition;
    protected int? MaxTurns => this.options.MaxTurns;

    protected int CurrentTurn { get; set; }

    protected List<AgentMessage> MessageThread;

    void IGroupChatHandler.AttachMessagePublishServicer(MessagePublishServicer? servicer)
    {
        this.PublishServicer = servicer;
    }

    private ValueTask PublishMessageAsync(GroupChatEventBase message, string topicType, CancellationToken cancellation = default)
    {
        return this.PublishServicer?.Invoke(message, topicType, cancellation) ?? ValueTask.CompletedTask;
    }

    protected ValueTask PublishMessageAsync(ChatMessage message, string topicType, CancellationToken cancellation = default)
    {
        return this.PublishMessageAsync(new GroupChatMessage { Message = message }, topicType, cancellation);
    }

    protected virtual async ValueTask ValidateGroupState(List<ChatMessage>? messages)
    {
    }

    public abstract ValueTask<string> SelectSpeakerAsync(List<AgentMessage> thread);

    public async ValueTask HandleAsync(GroupChatStart item, MessageContext messageContext)
    {
        if (this.TerminationCondition != null && this.TerminationCondition.IsTerminated)
        {
            // skipReset is used here to match the Python code
            await this.TerminateAsync("The chat has already terminated", skipReset: true);

            StopMessage earlyStop = new StopMessage
            {
                Content = "The chat has already terminated",
                Source = GroupChatBase<GroupChatManagerBase>.GroupChatManagerTopicType
            };

            await this.PublishMessageAsync(new GroupChatTermination { Message = earlyStop }, this.OutputTopicType);

            return;
        }

        if (item.Messages != null)
        {
            this.MessageThread.AddRange(item.Messages);
        }

        await this.ValidateGroupState(item.Messages);

        if (item.Messages != null)
        {
            await this.PublishMessageAsync(item, this.OutputTopicType);
            await this.PublishMessageAsync(item, this.GroupChatTopicType);

            // item.Messages is IList<ChatMessage> but we need IList<AgentMessage>
            // Unfortunately, IList does not support type variance, so we have to do this rather ugly thing
            // TODO: Check if we really need to have AgentMessage on the interface of ITerminationCondition
            List<AgentMessage> converted = [.. item.Messages.Cast<AgentMessage>()];

            if (await this.TerminateIfNeededAsync(converted))
            {
                return;
            }
        }

        await this.ProcessNextSpeakerAsync();
    }

    public async ValueTask HandleAsync(GroupChatAgentResponse item, MessageContext messageContext)
    {
        List<AgentMessage> delta = new List<AgentMessage>();

        if (item.AgentResponse.InnerMessages != null)
        {
            this.MessageThread.AddRange(item.AgentResponse.InnerMessages);
            delta.AddRange(item.AgentResponse.InnerMessages);
        }

        this.MessageThread.Add(item.AgentResponse.Message);
        delta.Add(item.AgentResponse.Message);

        if (await this.TerminateIfNeededAsync(delta))
        {
            return;
        }

        this.CurrentTurn++;
        if (this.MaxTurns.HasValue && this.MaxTurns.Value <= this.CurrentTurn)
        {
            await this.TerminateAsync($"Maximum number of turns ({this.MaxTurns.Value}) reached.");
            return;
        }

        await this.ProcessNextSpeakerAsync();
    }

    private ValueTask TerminateAsync(string message, bool skipReset = false)
    {
        StopMessage stopMessage = new StopMessage
        {
            Content = message,
            Source = GroupChatBase<GroupChatManagerBase>.GroupChatManagerTopicType
        };

        return this.TerminateAsync(stopMessage, skipReset);
    }

    private async ValueTask TerminateAsync(StopMessage stopMessage, bool skipReset = false)
    {
        await this.PublishMessageAsync(new GroupChatTermination { Message = stopMessage }, this.OutputTopicType);

        if (!skipReset)
        {
            this.TerminationCondition?.Reset();
            this.CurrentTurn = 0;
        }
    }

    private async ValueTask<bool> TerminateIfNeededAsync(params IList<AgentMessage> incomingMessages)
    {
        if (this.TerminationCondition == null)
        {
            return false;
        }

        StopMessage? stopMessage = await this.TerminationCondition.CheckAndUpdateAsync(incomingMessages);
        if (stopMessage != null)
        {
            await this.TerminateAsync(stopMessage);

            return true;
        }

        return false;
    }

    // TODO: Figure out how to route this to the right method
    //private ValueTask ProcessNextSpeakerAsync(params IList<AgentMessage> incomingMessages)
    //    => this.ProcessNextSpeakerAsync(incomingMessages);

    private async ValueTask ProcessNextSpeakerAsync()
    {
        string nextSpeakerTopic = await this.SelectSpeakerAsync(this.MessageThread);
        await this.PublishMessageAsync(new GroupChatRequestPublish { }, nextSpeakerTopic);
    }

    public ValueTask HandleAsync(object item, MessageContext messageContext)
    {
        throw new NotImplementedException();
    }
}
