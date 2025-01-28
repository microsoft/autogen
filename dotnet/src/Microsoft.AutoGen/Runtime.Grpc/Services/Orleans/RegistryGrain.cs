// Copyright (c) Microsoft Corporation. All rights reserved.
// RegistryGrain.cs
using Microsoft.AutoGen.Contracts;
using Microsoft.AutoGen.Runtime.Grpc.Abstractions;

namespace Microsoft.AutoGen.Runtime.Grpc;
internal sealed class RegistryGrain([PersistentState("state", "AgentRegistryStore")] IPersistentState<AgentsRegistryState> state) : Grain, IRegistryGrain
{
    private readonly Dictionary<IGateway, WorkerState> _workerStates = new();
    private readonly Dictionary<string, List<IGateway>> _supportedAgentTypes = [];
    private readonly Dictionary<(string Type, string Key), IGateway> _agentDirectory = [];
    private readonly TimeSpan _agentTimeout = TimeSpan.FromMinutes(1);

    public override Task OnActivateAsync(CancellationToken cancellationToken)
    {
        this.RegisterGrainTimer(static state => state.PurgeInactiveWorkers(), this, TimeSpan.FromSeconds(30), TimeSpan.FromSeconds(30));
        return base.OnActivateAsync(cancellationToken);
    }
    public ValueTask<List<string>> GetSubscribedAndHandlingAgentsAsync(string topic, string eventType)
    {
        List<string> agents = [];
        // get all agent types that are subscribed to the topic
        if (state.State.TopicToAgentTypesMap.TryGetValue(topic, out var subscribedAgentTypes))
        {
            /*// get all agent types that are handling the event
            if (state.State.EventsToAgentTypesMap.TryGetValue(eventType, out var handlingAgents))
            {
                agents.AddRange(subscribedAgentTypes.Intersect(handlingAgents).ToList());
            }*/
            agents.AddRange(subscribedAgentTypes.ToList());
        }
        if (state.State.TopicToAgentTypesMap.TryGetValue(eventType, out var eventHandlingAgents))
        {
            agents.AddRange(eventHandlingAgents.ToList());
        }
        if (state.State.TopicToAgentTypesMap.TryGetValue(topic + "." + eventType, out var combo))
        {
            agents.AddRange(combo.ToList());
        }
        // instead of an exact match, we can also check for a prefix match where key starts with the eventType
        if (state.State.TopicToAgentTypesMap.Keys.Any(key => key.StartsWith(eventType)))
        {
            state.State.TopicToAgentTypesMap.Where(
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
    public ValueTask<(IGateway? Worker, bool NewPlacement)> GetOrPlaceAgent(AgentId agentId)
    {
        // TODO: Clarify the logic
        bool isNewPlacement;
        if (!_agentDirectory.TryGetValue((agentId.Type, agentId.Key), out var worker) || !_workerStates.ContainsKey(worker))
        {
            worker = GetCompatibleWorkerCore(agentId.Type);
            if (worker is not null)
            {
                // New activation.
                _agentDirectory[(agentId.Type, agentId.Key)] = worker;
                isNewPlacement = true;
            }
            else
            {
                // No activation, and failed to place.
                isNewPlacement = false;
            }
        }
        else
        {
            // Existing activation.
            isNewPlacement = false;
        }
        return new((worker, isNewPlacement));
    }
    public ValueTask RemoveWorkerAsync(IGateway worker)
    {
        if (_workerStates.Remove(worker, out var state))
        {
            foreach (var type in state.SupportedTypes)
            {
                if (_supportedAgentTypes.TryGetValue(type, out var workers))
                {
                    workers.Remove(worker);
                }
            }
        }
        return ValueTask.CompletedTask;
    }
    public async ValueTask RegisterAgentTypeAsync(RegisterAgentTypeRequest registration, IGateway gateway)
    {
        if (!_supportedAgentTypes.TryGetValue(registration.Type, out var supportedAgentTypes))
        {
            supportedAgentTypes = _supportedAgentTypes[registration.Type] = [];
        }

        if (!supportedAgentTypes.Contains(gateway))
        {
            supportedAgentTypes.Add(gateway);
        }

        var workerState = GetOrAddWorker(gateway);
        workerState.SupportedTypes.Add(registration.Type);

        await state.WriteStateAsync().ConfigureAwait(false);
    }
    public ValueTask AddWorkerAsync(IGateway worker)
    {
        GetOrAddWorker(worker);
        return ValueTask.CompletedTask;
    }
    public async ValueTask UnregisterAgentType(string type, IGateway worker)
    {
        if (_workerStates.TryGetValue(worker, out var workerState))
        {
            workerState.SupportedTypes.Remove(type);
        }

        if (_supportedAgentTypes.TryGetValue(type, out var workers))
        {
            workers.Remove(worker);
        }
        await state.WriteStateAsync().ConfigureAwait(false);
    }
    private Task PurgeInactiveWorkers()
    {
        foreach (var (worker, state) in _workerStates)
        {
            if (DateTimeOffset.UtcNow - state.LastSeen > _agentTimeout)
            {
                _workerStates.Remove(worker);
                foreach (var type in state.SupportedTypes)
                {
                    if (_supportedAgentTypes.TryGetValue(type, out var workers))
                    {
                        workers.Remove(worker);
                    }
                }
            }
        }

        return Task.CompletedTask;
    }

    private WorkerState GetOrAddWorker(IGateway worker)
    {
        if (!_workerStates.TryGetValue(worker, out var workerState))
        {
            workerState = _workerStates[worker] = new();
        }

        workerState.LastSeen = DateTimeOffset.UtcNow;
        return workerState;
    }

    public ValueTask<IGateway?> GetCompatibleWorkerAsync(string type) => new(GetCompatibleWorkerCore(type));

    private IGateway? GetCompatibleWorkerCore(string type)
    {
        if (_supportedAgentTypes.TryGetValue(type, out var workers))
        {
            // Return a random compatible worker.
            return workers[Random.Shared.Next(workers.Count)];
        }

        return null;
    }
    public async ValueTask SubscribeAsync(AddSubscriptionRequest subscription)
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
                    state.State.AgentsToTopicsMap.TryGetValue(subscription.Subscription.TypeSubscription.AgentType, out var topics);
                    if (topics is null)
                    {
                        topics = new HashSet<string>();
                        state.State.AgentsToTopicsMap[subscription.Subscription.TypeSubscription.AgentType] = topics;
                    }
                    topics.Add(subscription.Subscription.TypeSubscription.TopicType);

                    // add the agent type to the set of agent types for the topic
                    state.State.TopicToAgentTypesMap.TryGetValue(subscription.Subscription.TypeSubscription.TopicType, out var agents);
                    if (agents is null)
                    {
                        agents = new HashSet<string>();
                        state.State.TopicToAgentTypesMap[subscription.Subscription.TypeSubscription.TopicType] = agents;
                    }
                    agents.Add(subscription.Subscription.TypeSubscription.AgentType);

                    // add the subscription by Guid
                    state.State.GuidSubscriptionsMap.TryGetValue(guid, out var existingSubscriptions);
                    if (existingSubscriptions is null)
                    {
                        existingSubscriptions = new HashSet<Subscription>();
                        state.State.GuidSubscriptionsMap[guid] = existingSubscriptions;
                    }
                    existingSubscriptions.Add(subscription.Subscription);
                    break;
                }
            default:
                throw new InvalidOperationException("Invalid subscription type");
        }
        await state.WriteStateAsync().ConfigureAwait(false);
    }
    public async ValueTask UnsubscribeAsync(RemoveSubscriptionRequest request)
    {
        var guid = request.Id;
        // does the guid parse?
        if (!Guid.TryParse(guid, out var _))
        {
            throw new InvalidOperationException("Invalid subscription id");
        }
        if (state.State.GuidSubscriptionsMap.TryGetValue(guid, out var subscriptions))
        {
            foreach (var subscription in subscriptions)
            {
                switch (subscription.SubscriptionCase)
                {
                    case Subscription.SubscriptionOneofCase.TypeSubscription:
                        {
                            // remove the topic from the set of topics for the agent type
                            state.State.AgentsToTopicsMap.TryGetValue(subscription.TypeSubscription.AgentType, out var topics);
                            topics?.Remove(subscription.TypeSubscription.TopicType);

                            // remove the agent type from the set of agent types for the topic
                            state.State.TopicToAgentTypesMap.TryGetValue(subscription.TypeSubscription.TopicType, out var agents);
                            agents?.Remove(subscription.TypeSubscription.AgentType);

                            //remove the subscription by Guid
                            state.State.GuidSubscriptionsMap.TryGetValue(guid, out var existingSubscriptions);
                            existingSubscriptions?.Remove(subscription);
                            break;
                        }
                    case Subscription.SubscriptionOneofCase.TypePrefixSubscription:
                        break;
                    default:
                        throw new InvalidOperationException("Invalid subscription type");
                }
            }
            state.State.GuidSubscriptionsMap.Remove(guid, out _);
        }
        await state.WriteStateAsync().ConfigureAwait(false);
    }
    public ValueTask<List<Subscription>> GetSubscriptionsAsync(GetSubscriptionsRequest request)
    {
        var _ = request;
        var subscriptions = new List<Subscription>();
        foreach (var kvp in state.State.GuidSubscriptionsMap)
        {
            subscriptions.AddRange(kvp.Value);
        }
        return new(subscriptions);
    }
    public ValueTask RegisterAgentTypeAsync(RegisterAgentTypeRequest request, IAgentRuntime worker)
    {
        var (_, _) = (request, worker);
        var e = "RegisterAgentTypeAsync(RegisterAgentTypeRequest request, IAgentRuntime worker) is not implemented when using the Grpc runtime.";
        throw new NotImplementedException(e);
    }
    public ValueTask UnregisterAgentTypeAsync(string type, IAgentRuntime worker)
    {
        var e = "UnregisterAgentTypeAsync(string type, IAgentRuntime worker) is not implemented when using the Grpc runtime.";
        throw new NotImplementedException(e);
    }
    private sealed class WorkerState
    {
        public HashSet<string> SupportedTypes { get; set; } = [];
        public DateTimeOffset LastSeen { get; set; }
    }
}

