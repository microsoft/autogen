// Copyright (c) Microsoft Corporation. All rights reserved.
// AgentsRegistryGrain.cs

using Microsoft.AutoGen.Contracts;

namespace Microsoft.AutoGen.Runtime.Grpc;
internal sealed class AgentsRegistryGrain([PersistentState("state", "AgentStateStore")] IPersistentState<AgentsRegistryState> state) : Grain, IRegistryGrain
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

    public ValueTask<IEnumerable<string>> GetSubscribedAndHandlingAgents(string topic,string eventType)
    {
        var subscribedAgents = state.State.TopicToAgentTypesMap[topic];
        var handlingAgents = state.State.EventsToAgentTypesMap[eventType];
        return ValueTask.FromResult(subscribedAgents.Intersect(handlingAgents));
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
    public ValueTask RegisterAgentType(RegisterAgentTypeRequest registration, IGateway worker)
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
        //_agentsToEventsMap.TryAdd(request.Type, new HashSet<string>(request.Events));
        //_agentsToTopicsMap.TryAdd(request.Type, new HashSet<string>(request.Topics));

        //// construct the inverse map for topics and agent types
        //foreach (var topic in request.Topics)
        //{
        //    _topicToAgentTypesMap.GetOrAdd(topic, _ => new HashSet<string>()).Add(request.Type);
        //}

        //// construct the inverse map for events and agent types
        //foreach (var evt in request.Events)
        //{
        //    _eventsToAgentTypesMap.GetOrAdd(evt, _ => new HashSet<string>()).Add(request.Type);
        //}
        return ValueTask.CompletedTask;
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

    private sealed class WorkerState
    {
        public HashSet<string> SupportedTypes { get; set; } = [];
        public DateTimeOffset LastSeen { get; set; }
    }
}
