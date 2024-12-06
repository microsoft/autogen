// Copyright (c) Microsoft Corporation. All rights reserved.
// GroupChatManagerBase.cs

using Microsoft.AutoGen.Abstractions;
using Microsoft.AutoGen.AgentChat.Abstractions;
using Microsoft.AutoGen.Agents;

namespace Microsoft.AutoGen.AgentChat.GroupChat;

public abstract class GroupChatManagerBase : SequentialRoutedAgent,
                                             IHandleEx<GroupChatStart>,
                                             IHandleEx<GroupChatAgentResponse>,
                                             IHandleDefault
{
    private string groupChatTopic;
    private string outputTopic;
    private List<string> participantTopics;
    private List<string> participantDescriptions;
    private List<AgentMessage> messageThread;
    private ITerminationCondition? terminationCondition;

    // It is kind of annoying that all child classes need to be aware of all of these objects to go up the stack
    // TODO: Should we replace all of these with IServiceCollection?
    public GroupChatManagerBase(IAgentRuntime context, EventTypes eventTypes, AgentChatBinder configurator) : base(context, eventTypes)
    {
        this.groupChatTopic = configurator.GroupChatTopic;
        this.outputTopic = configurator.OutputTopic;

        if (configurator.ParticipantTopics.Count() != configurator.ParticipantDescriptions.Count())
        {
            throw new ArgumentException("participantTopics and participantDescriptions must have the same number of elements");
        }

        HashSet<string> uniqueTopics = configurator.ParticipantTopics.ToHashSet();
        if (uniqueTopics.Count != configurator.ParticipantTopics.Count())
        {
            throw new ArgumentException("The participant topic ids must be unique.");
        }

        if (uniqueTopics.Contains(groupChatTopic))
        {
            throw new ArgumentException("The group topic id must not be in the participant topic ids.");
        }

        // TODO: Should we listify it early? Technically, Dictionary<> does not guarantee order
        this.participantTopics = configurator.ParticipantTopics.ToList();
        this.participantDescriptions = configurator.ParticipantDescriptions.ToList();

        this.messageThread = configurator.MessageThread ?? new List<AgentMessage>();
        this.terminationCondition = configurator.TerminationCondition;

        configurator.SubscribeGroup(this);
    }

    protected virtual async ValueTask ValidateGroupState(ChatMessage? message)
    {
    }

    public abstract ValueTask<string> SelectSpeakerAsync(List<AgentMessage> thread);

    public async ValueTask HandleAsync(GroupChatStart item, CancellationToken cancellationToken)
    {
        await this.PublishMessageAsync(item, this.groupChatTopic);

        if (this.terminationCondition != null && this.terminationCondition.IsTerminated)
        {
            StopMessage earlyStop = new StopMessage
            {
                Content = "The chat has already terminated",
                Source = "GroupChatManager"
            };

            await this.PublishMessageAsync(new GroupChatTermination { Message = earlyStop }, this.outputTopic);

            return;
        }

        if (item.Message != null)
        {
            this.messageThread.Add(item.Message);
        }

        await this.ValidateGroupState(item.Message);

        if (item.Message == null)
        {
            await this.ProcessNextSpeakerAsync();
        }
        else
        {
            await this.ProcessNextSpeakerAsync(item.Message);
        }
    }

    public ValueTask HandleAsync(GroupChatAgentResponse item, CancellationToken cancellationToken)
    {
        List<AgentMessage> delta = new List<AgentMessage>();

        if (item.AgentResponse.InnerMessages != null)
        {
            this.messageThread.AddRange(item.AgentResponse.InnerMessages);
            delta.AddRange(item.AgentResponse.InnerMessages);
        }

        this.messageThread.Add(item.AgentResponse.Message);
        delta.Add(item.AgentResponse.Message);

        return this.ProcessNextSpeakerAsync(delta);
    }

    private async ValueTask<bool> ShouldTerminateAsync(params IList<AgentMessage> incomingMessages)
    {
        if (this.terminationCondition == null)
        {
            return false;
        }

        StopMessage? stopMessage = await this.terminationCondition.UpdateAsync(incomingMessages);
        if (stopMessage != null)
        {
            await this.PublishMessageAsync(new GroupChatTermination { Message = stopMessage }, this.outputTopic);
            return true;
        }

        return false;
    }

    private async ValueTask ProcessNextSpeakerAsync(params IList<AgentMessage> incomingMessages)
    {
        if (!await this.ShouldTerminateAsync(incomingMessages))
        {
            string nextSpeakerTopic = await this.SelectSpeakerAsync(this.messageThread);
            await this.PublishMessageAsync(new GroupChatRequestPublish { }, nextSpeakerTopic);
        }
    }

    public ValueTask HandleAsync(object item, CancellationToken cancellationToken)
    {
        throw new InvalidOperationException($"Unhandled message in group chat manager: {item.GetType()}");
    }
}
