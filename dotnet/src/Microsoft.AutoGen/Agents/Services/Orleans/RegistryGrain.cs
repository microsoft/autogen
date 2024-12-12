// Copyright (c) Microsoft Corporation. All rights reserved.
// RegistryGrain.cs

using Microsoft.AutoGen.Contracts;

namespace Microsoft.AutoGen.Agents;

internal sealed class RegistryGrain : Grain, IRegistryGrain
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
    public ValueTask<(IGateway? Worker, bool NewPlacement)> GetOrPlaceAgent(AgentId agentId)
    {
        // TODO: 
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
    public ValueTask RegisterAgentType(string type, IGateway worker)
    {
        if (!_supportedAgentTypes.TryGetValue(type, out var supportedAgentTypes))
        {
            supportedAgentTypes = _supportedAgentTypes[type] = [];
        }

        if (!supportedAgentTypes.Contains(worker))
        {
            supportedAgentTypes.Add(worker);
        }
        var workerState = GetOrAddWorker(worker);
        workerState.SupportedTypes.Add(type);
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
