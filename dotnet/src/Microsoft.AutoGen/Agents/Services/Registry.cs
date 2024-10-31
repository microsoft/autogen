// Copyright (c) Microsoft Corporation. All rights reserved.
// Registry.cs

using Microsoft.AutoGen.Abstractions;
namespace Microsoft.AutoGen.Agents;
public class Registry : IAgentRegistry
{
    // InMemory Registry implementation
    private readonly Dictionary<string, List<IGateway>> _supportedAgentTypes = [];
    private readonly Dictionary<IGateway, WorkerState> _workerStates = [];
    private readonly Dictionary<(string Type, string Key), IGateway> _agentRegistryDirectory = [];

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
    private WorkerState GetOrAddWorker(IGateway worker)
    {
        if (!_workerStates.TryGetValue(worker, out var workerState))
        {
            workerState = _workerStates[worker] = new();
        }

        workerState.LastSeen = DateTimeOffset.UtcNow;
        return workerState;
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

    public ValueTask AddWorker(IGateway worker)
    {
        GetOrAddWorker(worker);
        return ValueTask.CompletedTask;
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

    private IGateway? GetCompatibleWorkerCore(string type)
    {
        if (_supportedAgentTypes.TryGetValue(type, out var workers))
        {
            // Return a random compatible worker.
            return workers[Random.Shared.Next(workers.Count)];
        }

        return null;
    }public ValueTask<(IGateway? Gateway, bool NewPlacment)> GetOrPlaceAgent(AgentId agentId)
    {
        // TODO: 
        bool isNewPlacement;
        if (!_agentRegistryDirectory.TryGetValue((agentId.Type, agentId.Key), out var worker) || !_workerStates.ContainsKey(worker))
        {
            worker = GetCompatibleWorkerCore(agentId.Type);
            if (worker is not null)
            {
                // New activation.
                _agentRegistryDirectory[(agentId.Type, agentId.Key)] = worker;
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
    private sealed class WorkerState
    {
        public HashSet<string> SupportedTypes { get; set; } = [];
        public DateTimeOffset LastSeen { get; set; }
    }
}