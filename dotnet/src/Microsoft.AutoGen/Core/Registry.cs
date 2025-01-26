// Copyright (c) Microsoft Corporation. All rights reserved.
// Registry.cs
using System.Xml;
using Microsoft.AutoGen.Contracts;
using Microsoft.Extensions.Logging;

namespace Microsoft.AutoGen.Core;
internal sealed class Registry : IRegistry
{
    private readonly Dictionary<(string Type, string Key), IAgentRuntime> _agentDirectory = [];
    private readonly Dictionary<string, HashSet<IAgentRuntime>> _supportedAgentTypes = [];
    private readonly TimeSpan _agentTimeout = TimeSpan.FromMinutes(1);
    private readonly IRegistryStorage Storage;
    private readonly AgentsRegistryState State;
    private readonly ILogger<Registry> _logger;
    private readonly string _registryETag;

    public Registry(IRegistryStorage storage, ILogger<Registry> logger)
    {
        _logger = logger;
        Storage = storage;
        State = Storage.ReadStateAsync().ConfigureAwait(true).GetAwaiter().GetResult();
        _registryETag = State.ETag;
        _logger.LogInformation("Registry initialized.");
    }

    public ValueTask<List<string>> GetSubscribedAndHandlingAgentsAsync(string topic, string eventType, CancellationToken cancellationToken = default)
    {
        List<string> agents = [];
        // get all agent types that are subscribed to the topic
        if (State.TopicToAgentTypesMap.TryGetValue(topic, out var subscribedAgentTypes))
        {
            /*// get all agent types that are handling the event
            if (State.EventsToAgentTypesMap.TryGetValue(eventType, out var handlingAgents))
            {
                agents.AddRange(subscribedAgentTypes.Intersect(handlingAgents).ToList());
            }*/
            agents.AddRange(subscribedAgentTypes.ToList());
        }
        if (State.TopicToAgentTypesMap.TryGetValue(eventType, out var eventHandlingAgents))
        {
            agents.AddRange(eventHandlingAgents.ToList());
        }
        if (State.TopicToAgentTypesMap.TryGetValue(topic + "." + eventType, out var combo))
        {
            agents.AddRange(combo.ToList());
        }
        // instead of an exact match, we can also check for a prefix match where key starts with the eventType
        if (State.TopicToAgentTypesMap.Keys.Any(key => key.StartsWith(eventType)))
        {
            State.TopicToAgentTypesMap.Where(
                kvp => kvp.Key.StartsWith(eventType))
                .SelectMany(kvp => kvp.Value)
                .Distinct()
                .ToList()
                .ForEach(async agentType =>
                {
                    agents.Add(agentType);
                });
        }
        agents = agents.Distinct().ToList();

        return new ValueTask<List<string>>(agents);
    }
    public async ValueTask RegisterAgentTypeAsync(RegisterAgentTypeRequest registration, IAgentRuntime runtime, CancellationToken cancellationToken = default)
    {
        if (!_supportedAgentTypes.TryGetValue(registration.Type, out var supportedAgentTypes))
        {
            supportedAgentTypes = _supportedAgentTypes[registration.Type] = [];
        }

        if (!supportedAgentTypes.Contains(runtime))
        {
            supportedAgentTypes.Add(runtime);
        }

        var workerState = GetOrAddWorker(runtime);
        workerState.SupportedTypes.Add(registration.Type);

        await Storage.WriteStateAsync(State).ConfigureAwait(false);
    }

    public ValueTask UnregisterAgentType(string type, IAgentRuntime worker)
    {
        if (_workerStates.TryGetValue(worker, out var state))
        {
            SupportedTypes.Remove(type);
        }

        if (_supportedAgentTypes.TryGetValue(type, out var workers))
        {
            workers.Remove(worker);
        }
        return ValueTask.CompletedTask;
    }
    public async ValueTask SubscribeAsync(AddSubscriptionRequest subscription, CancellationToken cancellationToken = default)
    {
        var guid = Guid.NewGuid().ToString();
        subscription.Subscription.Id = guid;
        switch (subscription.Subscription.SubscriptionCase)
        {
            //TODO: this doesnt look right
            case Subscription.SubscriptionOneofCase.TypePrefixSubscription:
                break;
            case Subscription.SubscriptionOneofCase.TypeSubscription:
                {
                    // add the topic to the set of topics for the agent type
                    State.AgentsToTopicsMap.TryGetValue(subscription.Subscription.TypeSubscription.AgentType, out var topics);
                    if (topics is null)
                    {
                        topics = new HashSet<string>();
                        State.AgentsToTopicsMap[subscription.Subscription.TypeSubscription.AgentType] = topics;
                    }
                    topics.Add(subscription.Subscription.TypeSubscription.TopicType);

                    // add the agent type to the set of agent types for the topic
                    State.TopicToAgentTypesMap.TryGetValue(subscription.Subscription.TypeSubscription.TopicType, out var agents);
                    if (agents is null)
                    {
                        agents = new HashSet<string>();
                        State.TopicToAgentTypesMap[subscription.Subscription.TypeSubscription.TopicType] = agents;
                    }
                    agents.Add(subscription.Subscription.TypeSubscription.AgentType);

                    // add the subscription by Guid
                    State.GuidSubscriptionsMap.TryGetValue(guid, out var existingSubscriptions);
                    if (existingSubscriptions is null)
                    {
                        existingSubscriptions = new HashSet<Subscription>();
                        State.GuidSubscriptionsMap[guid] = existingSubscriptions;
                    }
                    existingSubscriptions.Add(subscription.Subscription);
                    break;
                }
            default:
                throw new InvalidOperationException("Invalid subscription type");
        }
        await Storage.WriteStateAsync(State).ConfigureAwait(false);
    }
    public async ValueTask UnsubscribeAsync(RemoveSubscriptionRequest request)
    {
        var guid = request.Id;
        // does the guid parse?
        if (!Guid.TryParse(guid, out var _))
        {
            throw new InvalidOperationException("Invalid subscription id");
        }
        if (State.GuidSubscriptionsMap.TryGetValue(guid, out var subscriptions))
        {
            foreach (var subscription in subscriptions)
            {
                switch (subscription.SubscriptionCase)
                {
                    case Subscription.SubscriptionOneofCase.TypeSubscription:
                        {
                            // remove the topic from the set of topics for the agent type
                            State.AgentsToTopicsMap.TryGetValue(subscription.TypeSubscription.AgentType, out var topics);
                            topics?.Remove(subscription.TypeSubscription.TopicType);

                            // remove the agent type from the set of agent types for the topic
                            State.TopicToAgentTypesMap.TryGetValue(subscription.TypeSubscription.TopicType, out var agents);
                            agents?.Remove(subscription.TypeSubscription.AgentType);

                            //remove the subscription by Guid
                            State.GuidSubscriptionsMap.TryGetValue(guid, out var existingSubscriptions);
                            existingSubscriptions?.Remove(subscription);
                            break;
                        }
                    case Subscription.SubscriptionOneofCase.TypePrefixSubscription:
                        break;
                    default:
                        throw new InvalidOperationException("Invalid subscription type");
                }
            }
            State.GuidSubscriptionsMap.Remove(guid);
        }
        await Storage.WriteStateAsync(State).ConfigureAwait(false);
    }

    public ValueTask<List<Subscription>> GetSubscriptions(string agentType)
    {
        var subscriptions = new List<Subscription>();
        if (State.AgentsToTopicsMap.TryGetValue(agentType, out var topics))
        {
            foreach (var topic in topics)
            {
                subscriptions.Add(new Subscription
                {
                    TypeSubscription = new TypeSubscription
                    {
                        AgentType = agentType,
                        TopicType = topic
                    }
                });
            }
        }
        return new(subscriptions);
    }
    public ValueTask<List<Subscription>> GetSubscriptionsAsync(GetSubscriptionsRequest request)
    {
        var subscriptions = new List<Subscription>();
        foreach (var kvp in State.GuidSubscriptionsMap)
        {
            subscriptions.AddRange(kvp.Value);
        }
        return new(subscriptions);
    }
    private WriteAsync()
    {
        await Storage.WriteStateAsync(State).ConfigureAwait(false);
    }
}

