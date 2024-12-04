// Copyright (c) Microsoft Corporation. All rights reserved.
// SubscriptionsGrain.cs
using System.Collections.Concurrent;
using Microsoft.AutoGen.Abstractions;

namespace Microsoft.AutoGen.Agents;

internal sealed class SubscriptionsGrain([PersistentState("state", "PubSubStore")] IPersistentState<SubscriptionsState> subscriptionsState) : Grain, ISubscriptionsGrain
{
    private readonly IPersistentState<SubscriptionsState> _subscriptionsState = subscriptionsState;

    public ValueTask<ConcurrentDictionary<string, List<string>>> GetSubscriptionsAsync(string? agentType = null)
    {
        var _subscriptions = _subscriptionsState.State.Subscriptions;
        //if agentType is null, return all subscriptions else filter on agentType
        if (agentType != null)
        {
            var filteredSubscriptions = _subscriptions.Where(x => x.Value.Contains(agentType));
            return new ValueTask<ConcurrentDictionary<string, List<string>>>((ConcurrentDictionary<string, List<string>>)filteredSubscriptions);
        }
        return new ValueTask<ConcurrentDictionary<string, List<string>>>(_subscriptions);
    }
    public async ValueTask SubscribeAsync(string agentType, string topic)
    {
        await WriteSubscriptionsAsync(agentType: agentType, topic: topic, subscribe: true).ConfigureAwait(false);
    }
    public async ValueTask UnsubscribeAsync(string agentType, string topic)
    {
        await WriteSubscriptionsAsync(agentType: agentType, topic: topic, subscribe: false).ConfigureAwait(false);
    }
    private async ValueTask WriteSubscriptionsAsync(string agentType, string topic, bool subscribe=true)
    {
        var _subscriptions = _subscriptionsState.State.Subscriptions;
        if (!_subscriptions.TryGetValue(topic, out var agentTypes))
        {
            agentTypes = _subscriptions[topic] = [];
        }
        if (!agentTypes.Contains(agentType))
        {
            if (subscribe)
            {
                agentTypes.Add(agentType);
            }
            else
            {
                agentTypes.Remove(agentType);
            }
        }
        _subscriptions[topic] = agentTypes;
        _subscriptionsState.State.Subscriptions = _subscriptions;
        await _subscriptionsState.WriteStateAsync().ConfigureAwait(false);
    }
}