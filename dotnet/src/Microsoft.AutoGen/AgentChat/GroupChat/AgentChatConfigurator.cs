// Copyright (c) Microsoft Corporation. All rights reserved.
// ChatAgentContainer.cs

using Microsoft.AutoGen.AgentChat.Abstractions;

namespace Microsoft.AutoGen.AgentChat.GroupChat;

public struct AgentChatConfig(IChatAgent chatAgent, string parentTopic, string outputTopic)
{
    public IChatAgent ChatAgent { get; } = chatAgent;
    public string ParentTopic { get; } = parentTopic;
    public string OutputTopic { get; } = outputTopic;

    public string Name => this.ChatAgent.Name;
}

public class AgentChatConfigurator(string groupChatTopic, string outputTopic)
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

    public IEnumerable<AgentChatConfig> ParticipantConfigs => this.agentConfigs.Values;
    public List<AgentMessage>? MessageThread { get; set; }

    public IEnumerable<string> ParticipantTopics => this.ParticipantConfigs.Select(p => p.Name);
    public IEnumerable<string> ParticipantDescriptions => this.ParticipantConfigs.Select(p => p.ChatAgent.Description);
}
