// Copyright (c) Microsoft Corporation. All rights reserved.
// AgentsRegistry.cs

using Microsoft.AutoGen.Contracts;
using Microsoft.AutoGen.Runtime.Grpc.Abstractions;

namespace Microsoft.AutoGen.Runtime.Grpc;
internal sealed class AgentsRegistry([PersistentState("state", "AgentStateStore")] IPersistentState<AgentsRegistryState> state) : Grain, IGrainRegistry
{
    // TODO: use persistent state for some of these or (better) extend Orleans to implement some of this natively.
    private readonly Dictionary<IGateway, WorkerState> _workerStates = new();
    private readonly Dictionary<string, List<IGateway>> _supportedAgentTypes = [];
    private readonly Dictionary<(string Type, string Key), IGateway> _agentDirectory = [];
    private readonly TimeSpan _agentTimeout = TimeSpan.FromMinutes(1);

    public override Task OnActivateAsync(CancellationToken cancellationToken)
    {
        this.RegisterGrainTimer(static state => state.PurgeInactiveWorkers(), this, TimeSpan.FromSeconds(30), TimeSpan.FromSeconds(30));
        return base.OnActivateAsync(cancellationToken);
    }

    public ValueTask<List<string>> GetSubscribedAndHandlingAgents(string topic, string eventType)
    {
        // get all agent types that are subscribed to the topic
        var subscribedAgents = state.State.TopicToAgentTypesMap[topic];
        // get all agent types that are handling the event
        var handlingAgents = state.State.EventsToAgentTypesMap[eventType];
        // return the intersection of the two sets
        return new(subscribedAgents.Intersect(handlingAgents).ToList());
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
    public ValueTask RemoveWorker(IGateway worker)
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
    public async ValueTask RegisterAgentType(RegisterAgentTypeRequest registration, IGateway worker)
    {
        if (!_supportedAgentTypes.TryGetValue(registration.Type, out var supportedAgentTypes))
        {
            supportedAgentTypes = _supportedAgentTypes[registration.Type] = [];
        }

        if (!supportedAgentTypes.Contains(worker))
        {
            supportedAgentTypes.Add(worker);
        }

        var workerState = GetOrAddWorker(worker);
        workerState.SupportedTypes.Add(registration.Type);
        state.State.AgentsToEventsMap[registration.Type] = new HashSet<string>(registration.Events);
        state.State.AgentsToTopicsMap[registration.Type] = new HashSet<string>(registration.Topics);

        // construct the inverse map for topics and agent types
        foreach (var topic in registration.Topics)
        {
            if (!state.State.TopicToAgentTypesMap.TryGetValue(topic, out var topicSet))
            {
                topicSet = new HashSet<string>();
                state.State.TopicToAgentTypesMap[topic] = topicSet;
            }

            topicSet.Add(registration.Type);
        }

        // construct the inverse map for events and agent types
        foreach (var evt in registration.Events)
        {
            if (!state.State.EventsToAgentTypesMap.TryGetValue(evt, out var eventSet))
            {
                eventSet = new HashSet<string>();
                state.State.EventsToAgentTypesMap[evt] = eventSet;
            }

            eventSet.Add(registration.Type);
        }
        await state.WriteStateAsync().ConfigureAwait(false);
    }
    public ValueTask AddWorker(IGateway worker)
    {
        GetOrAddWorker(worker);
        return ValueTask.CompletedTask;
    }
    public ValueTask UnregisterAgentType(string type, IGateway worker)
    {
        if (_workerStates.TryGetValue(worker, out var state))
        {
            state.SupportedTypes.Remove(type);
        }

        if (_supportedAgentTypes.TryGetValue(type, out var workers))
        {
            workers.Remove(worker);
        }
        return ValueTask.CompletedTask;
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

    public ValueTask<IGateway?> GetCompatibleWorker(string type) => new(GetCompatibleWorkerCore(type));

    private IGateway? GetCompatibleWorkerCore(string type)
    {
        if (_supportedAgentTypes.TryGetValue(type, out var workers))
        {
            // Return a random compatible worker.
            return workers[Random.Shared.Next(workers.Count)];
        }

        return null;
    }

    public async ValueTask SubscribeAsync(AddSubscriptionRequest sub)
    {
        switch (sub.Subscription.SubscriptionCase)
        {
            case Subscription.SubscriptionOneofCase.TypePrefixSubscription:
                break;
            case Subscription.SubscriptionOneofCase.TypeSubscription:
                {
                    // add the topic to the set of topics for the agent type
                    state.State.AgentsToTopicsMap.TryGetValue(sub.Subscription.TypeSubscription.AgentType, out var topics);
                    if (topics is null)
                    {
                        topics = new HashSet<string>();
                        state.State.AgentsToTopicsMap[sub.Subscription.TypeSubscription.AgentType] = topics;
                    }
                    topics.Add(sub.Subscription.TypeSubscription.TopicType);

                    // add the agent type to the set of agent types for the topic
                    state.State.TopicToAgentTypesMap.TryGetValue(sub.Subscription.TypeSubscription.TopicType, out var agents);
                    if (agents is null)
                    {
                        agents = new HashSet<string>();
                        state.State.TopicToAgentTypesMap[sub.Subscription.TypeSubscription.TopicType] = agents;
                    }

                    agents.Add(sub.Subscription.TypeSubscription.AgentType);

                    break;
                }
            default:
                throw new InvalidOperationException("Invalid subscription type");
        }
        await state.WriteStateAsync().ConfigureAwait(false);
    }
    public async ValueTask UnsubscribeAsync(AddSubscriptionRequest request)
    {
        throw new NotImplementedException();
    }

    public ValueTask<Dictionary<string, List<string>>> GetSubscriptions(string agentType)
    {
        throw new NotImplementedException();
    }

    private sealed class WorkerState
    {
        public HashSet<string> SupportedTypes { get; set; } = [];
        public DateTimeOffset LastSeen { get; set; }
    }
}

