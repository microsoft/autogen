// Copyright (c) Microsoft Corporation. All rights reserved.
// Gateway.cs

using System.Collections.Concurrent;
using Microsoft.AutoGen.Abstractions;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;

namespace Microsoft.AutoGen.Agents;

internal class Gateway : BackgroundService, IGateway, IGrainWithIntegerKey
{
    private static readonly TimeSpan s_agentResponseTimeout = TimeSpan.FromSeconds(30);
    private readonly ILogger<Gateway> _logger;
    private readonly IClusterClient _clusterClient;
    private readonly IAgentRegistry _gatewayRegistry;
    private readonly IGateway _reference;

    private readonly ConcurrentDictionary<string, List<InMemoryQueue<CloudEvent>>> _supportedAgentTypes = [];
    private readonly ConcurrentDictionary<(string Type, string Key), InMemoryQueue<CloudEvent>> _agentDirectory = new();
    private readonly ConcurrentDictionary<InMemoryQueue<CloudEvent>, InMemoryQueue<CloudEvent>> _workers = new();
    private readonly ConcurrentDictionary<(InMemoryQueue<Message>, string), TaskCompletionSource<RpcResponse>> _pendingRequests = new();
    private readonly InMemoryQueue<Message> _messageQueue = new();

    public Gateway(IClusterClient clusterClient, ILogger<Gateway> logger)
    {
        _logger = logger;
        
        _clusterClient = clusterClient;
        _reference = clusterClient.CreateObjectReference<IGateway>(this);
        _gatewayRegistry = clusterClient.GetGrain<IAgentRegistry>(0);
    }

    public async ValueTask BroadcastEvent(CloudEvent evt, CancellationToken cancellationToken = default)
    {
        // TODO: filter the workers that receive the event
        var tasks = new List<Task>(_workers.Count);
        foreach (var (_, connection) in _workers)
        {
            tasks.Add(this.SendMessage(connection, evt, default));
        }
        await Task.WhenAll(tasks).ConfigureAwait(false);
    }

    private async Task SendMessage(IConnection connection, CloudEvent cloudEvent, CancellationToken cancellationToken = default)
    {
        var queue = (InMemoryQueue<CloudEvent>)connection;
        await queue.Writer.WriteAsync(cloudEvent, cancellationToken).AsTask();
    }

    public async ValueTask<RpcResponse> InvokeRequest(RpcRequest request, CancellationToken cancellationToken = default)
    {
        (string Type, string Key) agentId = (request.Target.Type, request.Target.Key);
        if (!_agentDirectory.TryGetValue(agentId, out var connection) || connection.Completion.IsCompleted)
        {
            // Activate the agent on a compatible worker process.
            if (_supportedAgentTypes.TryGetValue(request.Target.Type, out var workers))
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
    // Required to inherit from BackgroundService
    private void DispatchResponse(InMemoryQueue<Message> connection, RpcResponse response)
    {
        if (!_pendingRequests.TryRemove((connection, response.RequestId), out var completion))
        {
            _logger.LogWarning("Received response for unknown request.");
            return;
        }
        // Complete the request.
        completion.SetResult(response);
    }

    // Required to inherit from BackgroundService
    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        while (!stoppingToken.IsCancellationRequested)
        {
            try
            {
                await _gatewayRegistry.AddWorker(_reference);
            }
            catch (Exception exception)
            {
                _logger.LogWarning(exception, "Error adding worker to registry.");
            }

            await Task.Delay(TimeSpan.FromSeconds(15), stoppingToken);
        }

        try
        {
            await _gatewayRegistry.RemoveWorker(_reference);
        }
        catch (Exception exception)
        {
            _logger.LogWarning(exception, "Error removing worker from registry.");
        }
    }
    private async ValueTask DispatchEventAsync(CloudEvent evt)
    {
        await BroadcastEvent(evt);
        /*
        var topic = _clusterClient.GetStreamProvider("agents").GetStream<Event>(StreamId.Create(evt.Namespace, evt.Type));
        await topic.OnNextAsync(evt.ToEvent());
        */
    }

    private async ValueTask DispatchRequestAsync(InMemoryQueue<Message> connection, RpcRequest request)
    {
        var requestId = request.RequestId;
        if (request.Target is null)
        {
            throw new InvalidOperationException($"Request message is missing a target. Message: '{request}'.");
        }
        await InvokeRequestDelegate(connection, request, async request =>
        {
            var (gateway, isPlacement) = await _gatewayRegistry.GetOrPlaceAgent(request.Target);
            if (gateway is null)
            {
                return new RpcResponse { Error = "Agent not found and no compatible gateways were found." };
            }

            if (isPlacement)
            {
                // Activate the worker: load state
                // TODO
            }

            // Forward the message to the gateway and return the result.
            return await gateway.InvokeRequest(request);
        });
        //}
    }

    private static async Task InvokeRequestDelegate(InMemoryQueue<Message> connection, RpcRequest request, Func<RpcRequest, Task<RpcResponse>> func)
    {
        try
        {
            var response = await func(request);
            response.RequestId = request.RequestId;
            await connection.Writer.WriteAsync(new Message { Response = response });
        }
        catch (Exception ex)
        {
            await connection.Writer.WriteAsync(new Message { Response = new RpcResponse { RequestId = request.RequestId, Error = ex.Message } });
        }
    }
    public async ValueTask Store(AgentState value, CancellationToken cancellationToken = default)
    {
        var agentId = value.AgentId ?? throw new ArgumentNullException(nameof(value.AgentId));
        var agentState = _clusterClient.GetGrain<IWorkerAgentGrain>($"{agentId.Type}:{agentId.Key}");
        await agentState.WriteStateAsync(value, value.ETag);
    }

    public async ValueTask<AgentState> Read(AgentId agentId, CancellationToken cancellationToken = default)
    {
        var agentState = _clusterClient.GetGrain<IWorkerAgentGrain>($"{agentId.Type}:{agentId.Key}");
        return await agentState.ReadStateAsync();
    }
}
