// Copyright (c) Microsoft Corporation. All rights reserved.
// AgentWorker.cs

using System.Collections.Concurrent;
using Microsoft.AutoGen.Abstractions;
using Microsoft.Extensions.Logging;

namespace Microsoft.AutoGen.Agents;

public class AgentWorker : IAgentWorker
{
    private static readonly TimeSpan s_agentResponseTimeout = TimeSpan.FromSeconds(30);
    private readonly ILogger<AgentWorker> _logger;
    private readonly InMemoryQueue<CloudEvent> _eventsQueue = new();
    private readonly InMemoryQueue<Message> _messageQueue = new();
    private readonly ConcurrentDictionary<string, AgentState> _agentStates = new();
    private readonly Dictionary<string, List<IWorkerGateway>> _supportedAgentTypes = [];
    private readonly ConcurrentDictionary<string, List<InMemoryQueue<CloudEvent>>> _gatewaySupportedAgentTypes = [];

    private readonly Dictionary<IWorkerGateway, WorkerState> _workerStates = [];
    private readonly ConcurrentDictionary<(string Type, string Key), InMemoryQueue<CloudEvent>> _agentDirectory = new();
    private readonly Dictionary<(string Type, string Key), IWorkerGateway> _agentRegistryDirectory = [];

    private readonly ConcurrentDictionary<InMemoryQueue<CloudEvent>, InMemoryQueue<CloudEvent>> _workers = new();
    private readonly ConcurrentDictionary<string, (IAgentBase Agent, string OriginalRequestId)> _pendingClientRequests = new();
    private readonly ConcurrentDictionary<(InMemoryQueue<Message>, string), TaskCompletionSource<RpcResponse>> _pendingRequests = new();

    public AgentWorker(ILogger<AgentWorker> logger)
    {
        _logger = logger;
    }
    public async ValueTask PublishEventAsync(CloudEvent evt, CancellationToken cancellationToken = default)
    {
        await _eventsQueue.Writer.WriteAsync(evt);
    }

    public ValueTask SendRequest(IAgentBase agent, RpcRequest request)
    {
        _logger.LogInformation("[{AgentId}] Sending request '{Request}'.", agent.AgentId, request);
        var requestId = Guid.NewGuid().ToString();
        _pendingClientRequests[requestId] = (agent, request.RequestId);
        request.RequestId = requestId;
        return this.WriteAsync(new Message { Request = request });
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

    // IWorkerGateway implementation
    public async ValueTask<RpcResponse> InvokeRequest(RpcRequest request)
    {
        (string Type, string Key) agentId = (request.Target.Type, request.Target.Key);
        if (!_agentDirectory.TryGetValue(agentId, out var connection) || connection.Completion.IsCompleted)
        {
            // Activate the agent on a compatible worker process.
            if (_gatewaySupportedAgentTypes.TryGetValue(request.Target.Type, out var workers))
            {
                connection = workers[Random.Shared.Next(workers.Count)];
                _agentDirectory[agentId] = connection;
            }
            else
            {
                return new(new RpcResponse { Error = "Agent not found." });
            }
        }

        // Proxy the request to the agent.
        var originalRequestId = request.RequestId;
        var newRequestId = Guid.NewGuid().ToString();
        var completion = _pendingRequests[(_messageQueue, newRequestId)] = new(TaskCreationOptions.RunContinuationsAsynchronously);
        request.RequestId = newRequestId;
        await _messageQueue.Writer.WriteAsync(new Message { Request = request });

        // Wait for the response and send it back to the caller.
        var response = await completion.Task.WaitAsync(s_agentResponseTimeout);
        response.RequestId = originalRequestId;
        return response;
    }
    public async ValueTask BroadcastEvent(CloudEvent evt)
    {
        // TODO: filter the workers that receive the event
        var tasks = new List<Task>(_workers.Count);
        foreach (var (_, connection) in _workers)
        {
            tasks.Add(connection.Writer.WriteAsync(evt).AsTask());
        }

        await Task.WhenAll(tasks).ConfigureAwait(false);
    }
    private sealed class WorkerState
    {
        public HashSet<string> SupportedTypes { get; set; } = [];
        public DateTimeOffset LastSeen { get; set; }
    }

    // In-Memory specific implementations
    private ValueTask WriteAsync(Message message)
    {
        return _messageQueue.Writer.WriteAsync(message);
    }
}
