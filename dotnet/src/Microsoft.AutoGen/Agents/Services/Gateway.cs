// Copyright (c) Microsoft Corporation. All rights reserved.
// Gateway.cs
using System.Collections.Concurrent;
using Microsoft.AutoGen.Abstractions;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;

namespace Microsoft.AutoGen.Agents;

internal class Gateway : BackgroundService, IGateway, IGrainWithIntegerKey
{
    //TODO: make configurable
    private static readonly TimeSpan s_agentResponseTimeout = TimeSpan.FromSeconds(30);
    private readonly ILogger<Gateway> _logger;
    private readonly IAgentRegistry _gatewayRegistry;
    private readonly IGateway _reference;
    private readonly ConcurrentDictionary<string, AgentState> _agentState = new();
    private readonly ConcurrentDictionary<string, List<InMemoryQueue<Message>>> _supportedAgentTypes = [];
    private readonly ConcurrentDictionary<(string Type, string Key), InMemoryQueue<Message>> _agentDirectory = new();
    public readonly ConcurrentDictionary<IConnection, IConnection> _workers = new();
    private readonly ConcurrentDictionary<(InMemoryQueue<Message>, string), TaskCompletionSource<RpcResponse>> _pendingRequests = new();
    public Gateway(ILogger<Gateway> logger, IAgentRegistry gatewayRegistry)
    {
        _logger = logger;
        _gatewayRegistry = gatewayRegistry;
        _reference = this;
    }
    public Task<IAgentRegistry> GetRegistry() => Task.FromResult(_gatewayRegistry);
    public async ValueTask BroadcastEvent(CloudEvent evt, CancellationToken cancellationToken = default)
    {
        // TODO: filter the workers that receive the event
        var tasks = new List<Task>(_workers.Count);
        foreach (var (_, connection) in _supportedAgentTypes)
        {

            tasks.Add(this.SendMessageAsync((IConnection)connection[0], evt, default));
        }
        await Task.WhenAll(tasks).ConfigureAwait(false);
    }

    // intentionally not static
    public virtual async Task SendMessageAsync(IConnection connection, CloudEvent cloudEvent, CancellationToken cancellationToken = default)
    {
        var queue = (InMemoryQueue<Message>)connection;
        await queue.Writer.WriteAsync(new Message { CloudEvent = cloudEvent }, cancellationToken).AsTask().ConfigureAwait(false);
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
        var completion = _pendingRequests[(connection, newRequestId)] = new(TaskCreationOptions.RunContinuationsAsynchronously);
        request.RequestId = newRequestId;
        await connection.Writer.WriteAsync(new Message { Request = request });
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
    internal Task ConnectToWorkerProcess(InMemoryQueue<Message> channel, string type)
    {
        _logger.LogInformation("Received new connection from {type}.", type);
        _workers[channel] = channel;
        return Task.CompletedTask;
    }
    public async ValueTask StoreAsync(AgentState value, CancellationToken cancellationToken = default)
    {
        var agentId = value.AgentId ?? throw new ArgumentNullException(nameof(value.AgentId));
        _agentState[agentId.Key] = value;
    }

    public async ValueTask<AgentState> ReadAsync(AgentId agentId, CancellationToken cancellationToken = default)
    {
        if (_agentState.TryGetValue(agentId.Key, out var state))
        {
            return state;
        }
        return new AgentState { AgentId = agentId };
    }
}
