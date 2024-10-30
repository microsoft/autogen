// Copyright (c) Microsoft Corporation. All rights reserved.
// InMemoryAgentWorkerRuntime.cs

using System.Collections.Concurrent;
using System.Diagnostics;
using Microsoft.AutoGen.Abstractions;
using Microsoft.AutoGen.Runtime;
using Microsoft.Extensions.Logging;

namespace Microsoft.AutoGen.Agents;

public class InMemoryAgentWorkerRuntime : IAgentWorkerRuntime, IAgentWorkerRegistryGrain, IWorkerGateway, IAgentContext
{
    private readonly ILogger<InMemoryAgentWorkerRuntime> _logger;
    private readonly InMemoryQueue<CloudEvent> _eventsQueue = new();
    private readonly InMemoryQueue<Message> _messageQueue = new();
    private readonly ConcurrentDictionary<string, AgentState> _agentStates = new();
    private readonly Dictionary<string, List<IWorkerGateway>> _supportedAgentTypes = [];
    private readonly Dictionary<IWorkerGateway, WorkerState> _workerStates = [];
    private readonly ConcurrentDictionary<string, (IAgentBase Agent, string RequestId)> _pendingRequests = new();
    private readonly ConcurrentDictionary<AgentId, IWorkerGateway> _agentPlacements = new();
    private readonly Dictionary<(string Type, string Key), IWorkerGateway> _agentDirectory = [];

    AgentId IAgentContext.AgentId => throw new NotImplementedException();

    IAgentBase? IAgentContext.AgentInstance { get => throw new NotImplementedException(); set => throw new NotImplementedException(); }

    DistributedContextPropagator IAgentContext.DistributedContextPropagator => throw new NotImplementedException();

    ILogger IAgentContext.Logger => _logger;

    public InMemoryAgentWorkerRuntime(ILogger<InMemoryAgentWorkerRuntime> logger)
    {
        _logger = logger;
    }

    // IAgentWorkerRuntime implementation
    public async ValueTask PublishEventAsync(CloudEvent evt)
    {
        await _eventsQueue.Writer.WriteAsync(evt);
    }

    public ValueTask SendRequest(IAgentBase agent, RpcRequest request)
    {
        _logger.LogInformation("[{AgentId}] Sending request '{Request}'.", agent.AgentId, request);
        var requestId = Guid.NewGuid().ToString();
        _pendingRequests[requestId] = (agent, request.RequestId);
        request.RequestId = requestId;
        return _messageQueue.Writer.WriteAsync(new Message { Request = request });
    }

    public ValueTask SendResponse(RpcResponse response)
    {
        _logger.LogInformation("Sending response '{Response}'.", response);
        return _messageQueue.Writer.WriteAsync(new Message { Response = response });
    }

    public ValueTask Store(AgentState value)
    {
        var agentId = value.AgentId ?? throw new InvalidOperationException("AgentId is required when saving AgentState.");
        var response = _agentStates.TryAdd(agentId.ToString(), value);
        if (!response)
        {
            throw new InvalidOperationException($"Error saving AgentState for AgentId {agentId}.");
        }
        return ValueTask.CompletedTask;
    }

    public ValueTask<AgentState> Read(AgentId agentId)
    {
        _agentStates.TryGetValue(agentId.ToString(), out var state);
        //        if (response.Success && response.AgentState.AgentId is not null) - why is success always false?
        if (state is not null && state.AgentId is not null)
        {
            return new ValueTask<AgentState>(state);
        }
        else
        {
            throw new KeyNotFoundException($"Failed to read AgentState for {agentId}.");
        }
    }

    // IAgentWorkerRegistryGrain implementation
    public ValueTask RegisterAgentType(string type, IWorkerGateway worker)
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
    private WorkerState GetOrAddWorker(IWorkerGateway worker)
    {
        if (!_workerStates.TryGetValue(worker, out var workerState))
        {
            workerState = _workerStates[worker] = new();
        }

        workerState.LastSeen = DateTimeOffset.UtcNow;
        return workerState;
    }
    public ValueTask UnregisterAgentType(string type, IWorkerGateway worker)
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

    public ValueTask AddWorker(IWorkerGateway worker)
    {
        GetOrAddWorker(worker);
        return ValueTask.CompletedTask;
    }

    public ValueTask RemoveWorker(IWorkerGateway worker)
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

    private IWorkerGateway? GetCompatibleWorkerCore(string type)
    {
        if (_supportedAgentTypes.TryGetValue(type, out var workers))
        {
            // Return a random compatible worker.
            return workers[Random.Shared.Next(workers.Count)];
        }

        return null;
    }public ValueTask<(IWorkerGateway? Gateway, bool NewPlacment)> GetOrPlaceAgent(AgentId agentId)
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

    // IWorkerGateway implementation
    public ValueTask<RpcResponse> InvokeRequest(RpcRequest request)
    {
        // Implement in-memory request invocation logic
        return ValueTask.FromResult(new RpcResponse());
    }

    public ValueTask BroadcastEvent(CloudEvent evt)
    {
        // Implement in-memory event broadcasting logic
        return ValueTask.CompletedTask;
    }

    public ValueTask Store(AgentState value)
    {
        // Implement in-memory state storing logic
        return ValueTask.CompletedTask;
    }

    public ValueTask<AgentState> Read(AgentId agentId)
    {
        // Implement in-memory state reading logic
        return ValueTask.FromResult(new AgentState());
    }

    ValueTask IAgentContext.Store(AgentState value)
    {
        throw new NotImplementedException();
    }

    ValueTask<AgentState> IAgentContext.Read(AgentId agentId)
    {
        throw new NotImplementedException();
    }

    ValueTask IAgentContext.SendResponseAsync(RpcRequest request, RpcResponse response)
    {
        throw new NotImplementedException();
    }

    ValueTask IAgentContext.SendRequestAsync(IAgentBase agent, RpcRequest request)
    {
        throw new NotImplementedException();
    }

    async ValueTask IAgentContext.PublishEventAsync(CloudEvent @event)
    {
        await _eventsQueue.Writer.WriteAsync(@event);
    }
    private sealed class WorkerState
    {
        public HashSet<string> SupportedTypes { get; set; } = [];
        public DateTimeOffset LastSeen { get; set; }
    }
}
