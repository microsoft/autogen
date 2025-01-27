// Copyright (c) Microsoft Corporation. All rights reserved.
// IAgentRuntime.cs

using StateDict = System.Collections.Generic.IDictionary<string, object>;

namespace Microsoft.AutoGen.Contracts.Python;

public interface IAgentRuntime : ISaveState<IAgentRuntime>
{
    public ValueTask<object> SendMessageAsync(object message, AgentId recepient, AgentId? sender = null, string? messageId = null, CancellationToken? cancellationToken = default);
    public ValueTask<object> PublishMessageAsync(object message, TopicId topic, AgentId? sender = null, string? messageId = null, CancellationToken? cancellationToken = default);

    // TODO: Can we call this Resolve?
    public ValueTask<AgentId> GetAgentAsync(AgentId agentId, string key = "default", bool lazy = true/*, CancellationToken? = default*/);
    public ValueTask<AgentId> GetAgentAsync(AgentType agentType, string key = "default", bool lazy = true/*, CancellationToken? = default*/);
    public ValueTask<AgentId> GetAgentAsync(string agent, string key = "default", bool lazy = true/*, CancellationToken? = default*/);

    public ValueTask<StateDict> SaveAgentStateAsync(/*CancellationToken? cancellationToken = default*/);
    public ValueTask LoadAgentStateAsync(StateDict state/*, CancellationToken? cancellationToken = default*/);

    public ValueTask<AgentMetadata> GetAgentMetadataAsync(AgentId agentId/*, CancellationToken? cancellationToken = default*/);

    public ValueTask AddSubscriptionAsync(ISubscriptionDefinition subscription/*, CancellationToken? cancellationToken = default*/);
    public ValueTask RemoveSubscriptionAsync(string subscriptionId/*, CancellationToken? cancellationToken = default*/);

    public ValueTask<AgentType> RegisterAgentFactoryAsync<TAgent>(AgentType type, Func<ValueTask<TAgent>> factoryFunc) where TAgent : IHostableAgent;

    // TODO:
    //public ValueTask<TAgent> TryGetUnderlyingAgentInstanceAsync<TAgent>(AgentId agentId) where TAgent : IHostableAgent;
    //public void AddMessageSerializer(params object[] serializers);

    // Extras
    public ValueTask<IAgent> TryGetAgentProxyAsync(AgentId agentId);
}

