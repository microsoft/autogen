// Copyright (c) Microsoft Corporation. All rights reserved.
// SubscriptionsGrain.cs
using System.Collections.Concurrent;
using Microsoft.AutoGen.Abstractions;

namespace Microsoft.AutoGen.Agents;

internal sealed class SubscriptionsGrain([PersistentState("state", "PubSubStore")] IPersistentState<SubscriptionsState> subscriptionsState) : Grain, ISubscriptionsGrain
{
    private readonly IPersistentState<SubscriptionsState> _subscriptionsState = subscriptionsState;

    public ValueTask<ConcurrentDictionary<string, List<string>>> GetSubscriptionsByAgentTypeAsync(string? agentType = null)
    {
        var _subscriptions = _subscriptionsState.State.SubscriptionsByAgentType;
        //if agentType is null, return all subscriptions else filter on agentType
        if (agentType != null)
        {
            var filteredSubscriptions = _subscriptions.Where(x => x.Value.Contains(agentType));
            return ValueTask.FromResult<ConcurrentDictionary<string, List<string>>>((ConcurrentDictionary<string, List<string>>)filteredSubscriptions);
        }
        return ValueTask.FromResult<ConcurrentDictionary<string, List<string>>>(_subscriptions);
    }
    public ValueTask<ConcurrentDictionary<string, List<string>>> GetSubscriptionsByTopicAsync(string? topic = null)
    {
        var _subscriptions = _subscriptionsState.State.SubscriptionsByTopic;
        //if topic is null, return all subscriptions else filter on topic
        if (topic != null)
        {
            var filteredSubscriptions = _subscriptions.Where(x => x.Key == topic);
            return ValueTask.FromResult<ConcurrentDictionary<string, List<string>>>((ConcurrentDictionary<string, List<string>>)filteredSubscriptions);
        }
        return ValueTask.FromResult<ConcurrentDictionary<string, List<string>>>(_subscriptions);
    }
    public ValueTask<SubscriptionsState> GetSubscriptionsStateAsync() => ValueTask.FromResult(_subscriptionsState.State);

    public async ValueTask SubscribeAsync(string agentType, string topic)
    {
        await WriteSubscriptionsAsync(agentType: agentType, topic: topic, subscribe: true).ConfigureAwait(false);
    }
    public async ValueTask UnsubscribeAsync(string agentType, string topic)
    {
        await WriteSubscriptionsAsync(agentType: agentType, topic: topic, subscribe: false).ConfigureAwait(false);
    }
    public async ValueTask WriteSubscriptionsStateAsync(SubscriptionsState subscriptionsState)
    {
        _subscriptionsState.State = subscriptionsState;
        await _subscriptionsState.WriteStateAsync().ConfigureAwait(true);
    }

    private async ValueTask WriteSubscriptionsAsync(string agentType, string topic, bool subscribe=true)
    {
        var _subscriptions = await GetSubscriptionsByAgentTypeAsync().ConfigureAwait(true);
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
        _subscriptionsState.State.SubscriptionsByAgentType = _subscriptions;
        var _subsByTopic = await GetSubscriptionsByTopicAsync().ConfigureAwait(true);
        _subsByTopic.GetOrAdd(topic, _ => []).Add(agentType);
        _subscriptionsState.State.SubscriptionsByTopic = _subsByTopic;
        await _subscriptionsState.WriteStateAsync().ConfigureAwait(false);
    }
}