// Copyright (c) Microsoft Corporation. All rights reserved.
// AgentChatBinder.cs

using Microsoft.AutoGen.Abstractions;
using Microsoft.AutoGen.AgentChat.Abstractions;
using Microsoft.Azure.Cosmos.Core;

namespace Microsoft.AutoGen.AgentChat.GroupChat;

public struct AgentChatConfig(IChatAgent chatAgent, string parentTopic, string outputTopic)
{
    public string ParentTopic { get; } = parentTopic;
    public string OutputTopic { get; } = outputTopic;

    public IChatAgent ChatAgent { get; } = chatAgent;

    public string Name => this.ChatAgent.Name;
}

public class AgentChatBinder(string groupChatTopic, string outputTopic, CancellationToken cancel = default)
{
    private readonly Dictionary<string, AgentChatConfig> agentConfigs = new Dictionary<string, AgentChatConfig>();

    public string GroupChatTopic { get; } = groupChatTopic;
    public string OutputTopic { get; } = outputTopic;

    public ITerminationCondition? TerminationCondition { get; set; }

    public AgentChatConfig this[string name]
    {
        get => this.agentConfigs[name];
        set => this.agentConfigs[name] = value;
    }

    public AsyncQueue<AgentMessage?> OutputQueue { get; } = new AsyncQueue<AgentMessage?>(cancel);
    public string? StopReason { get; set; }

    internal void SubscribeGroup(IAgentBase agent)
    {
        _ = agent.Subscribe(this.GroupChatTopic);
    }

    internal void SubscribeOutput(OutputCollectorAgent outputCollector)
    {
        _ = outputCollector.Subscribe(this.OutputTopic);
    }

    public IEnumerable<AgentChatConfig> ParticipantConfigs => this.agentConfigs.Values;
    public List<AgentMessage>? MessageThread { get; set; }

    public IEnumerable<string> ParticipantTopics => this.ParticipantConfigs.Select(p => p.Name);
    public IEnumerable<string> ParticipantDescriptions => this.ParticipantConfigs.Select(p => p.ChatAgent.Description);
}
