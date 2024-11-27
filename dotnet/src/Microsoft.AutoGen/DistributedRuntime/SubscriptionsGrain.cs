// Copyright (c) Microsoft Corporation. All rights reserved.
// SubscriptionsGrain.cs

namespace Microsoft.AutoGen.Agents;

internal sealed class SubscriptionsGrain([PersistentState("state", "PubSubStore")] IPersistentState<SubscriptionsState> state) : Grain, ISubscriptionsGrain
{
    private readonly Dictionary<string, List<string>> _subscriptions = new();
    public ValueTask<Dictionary<string, List<string>>> GetSubscriptions(string? agentType = null)
    {
        //if agentType is null, return all subscriptions else filter on agentType
        if (agentType != null)
        {
            return new ValueTask<Dictionary<string, List<string>>>(_subscriptions.Where(x => x.Value.Contains(agentType)).ToDictionary(x => x.Key, x => x.Value));
        }
        return new ValueTask<Dictionary<string, List<string>>>(_subscriptions);
    }
    public ValueTask Subscribe(string agentType, string topic)
    {
        if (!_subscriptions.TryGetValue(topic, out var subscriptions))
        {
            subscriptions = _subscriptions[topic] = [];
        }
        if (!subscriptions.Contains(agentType))
        {
            subscriptions.Add(agentType);
        }
        _subscriptions[topic] = subscriptions;
        state.State.Subscriptions = _subscriptions;
        state.WriteStateAsync();

        return ValueTask.CompletedTask;
    }
    public ValueTask Unsubscribe(string agentType, string topic)
    {
        if (!_subscriptions.TryGetValue(topic, out var subscriptions))
        {
            subscriptions = _subscriptions[topic] = [];
        }
        if (!subscriptions.Contains(agentType))
        {
            subscriptions.Remove(agentType);
        }
        _subscriptions[topic] = subscriptions;
        state.State.Subscriptions = _subscriptions;
        state.WriteStateAsync();
        return ValueTask.CompletedTask;
    }
}
public sealed class SubscriptionsState
{
    public Dictionary<string, List<string>> Subscriptions { get; set; } = new();
}
