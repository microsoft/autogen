// Copyright (c) Microsoft Corporation. All rights reserved.
// GrpcGateway.cs

using System.Collections.Concurrent;
using Grpc.Core;
using Microsoft.AutoGen.Contracts;
using Microsoft.AutoGen.Protobuf;
using Microsoft.AutoGen.RuntimeGateway.Grpc.Abstractions;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;

namespace Microsoft.AutoGen.RuntimeGateway.Grpc;

public sealed class GrpcGateway : BackgroundService, IGateway
{
    private static readonly TimeSpan s_agentResponseTimeout = TimeSpan.FromSeconds(30);
    private readonly ILogger<GrpcGateway> _logger;
    private readonly IClusterClient _clusterClient;
    //private readonly ConcurrentDictionary<string, AgentState> _agentState = new();
    private readonly IRegistryGrain _gatewayRegistry;
    private readonly IGateway _reference;
    // The agents supported by each worker process.
    private readonly ConcurrentDictionary<string, List<GrpcWorkerConnection>> _supportedAgentTypes = [];
    public readonly ConcurrentDictionary<string, GrpcWorkerConnection> _workers = new();
    internal readonly ConcurrentDictionary<string, GrpcWorkerConnection> _workersByConnection = new();
    private readonly ConcurrentDictionary<string, Subscription> _subscriptionsByAgentType = new();
    private readonly ConcurrentDictionary<string, List<string>> _subscriptionsByTopic = new();
    private readonly ISubscriptionsGrain _subscriptions;

    // The mapping from agent id to worker process.
    private readonly ConcurrentDictionary<(string Type, string Key), GrpcWorkerConnection> _agentDirectory = new();
    // RPC
    private readonly ConcurrentDictionary<(GrpcWorkerConnection, string), TaskCompletionSource<RpcResponse>> _pendingRequests = new();
    public GrpcGateway(IClusterClient clusterClient, ILogger<GrpcGateway> logger)
    {
        _logger = logger;
        _clusterClient = clusterClient;
        _reference = clusterClient.CreateObjectReference<IGateway>(this);
        _gatewayRegistry = clusterClient.GetGrain<IRegistryGrain>(0);
        _subscriptions = clusterClient.GetGrain<ISubscriptionsGrain>(0);
    }
    public async ValueTask<RpcResponse> InvokeRequestAsync(RpcRequest request, CancellationToken cancellationToken = default)
    {
        var agentId = (request.Target.Type, request.Target.Key);
        if (!_agentDirectory.TryGetValue(agentId, out var connection) || connection.Completion.IsCompleted == true)
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
        await connection.ResponseStream.WriteAsync(new Message { Request = request }, cancellationToken).ConfigureAwait(false);
        // Wait for the response and send it back to the caller.
        var response = await completion.Task.WaitAsync(s_agentResponseTimeout);
        response.RequestId = originalRequestId;
        return response;
    }
    public async ValueTask StoreAsync(AgentState value, CancellationToken cancellationToken = default)
    {
        _ = value.AgentId ?? throw new ArgumentNullException(nameof(value.AgentId));
        var agentState = _clusterClient.GetGrain<IAgentGrain>($"{value.AgentId.Type}:{value.AgentId.Key}");
        await agentState.WriteStateAsync(value, value.ETag);
    }
    public async ValueTask<AgentState> ReadAsync(Protobuf.AgentId agentId, CancellationToken cancellationToken = default)
    {
        var agentState = _clusterClient.GetGrain<IAgentGrain>($"{agentId.Type}:{agentId.Key}");
        return await agentState.ReadStateAsync();
    }
    public async ValueTask<RegisterAgentTypeResponse> RegisterAgentTypeAsync(RegisterAgentTypeRequest request, ServerCallContext context, CancellationToken cancellationToken = default)
    {
        try
        {
            var clientId = context.RequestHeaders.Get("client-id")?.Value ??
                throw new RpcException(new Status(StatusCode.InvalidArgument, "Grpc Client ID is required."));
            if (!_workers.TryGetValue(clientId, out var connection))
            {
                throw new RpcException(new Status(StatusCode.InvalidArgument, $"Grpc Worker Connection not found for ClientId {clientId}."));
            }
            connection.AddSupportedType(request.Type);
            _supportedAgentTypes.GetOrAdd(request.Type, _ => []).Add(connection);

            await _gatewayRegistry.RegisterAgentTypeAsync(request, _reference).ConfigureAwait(true);
            return new RegisterAgentTypeResponse {};
        }
        catch (Exception ex)
        {
            throw new RpcException(new Status(StatusCode.Internal, ex.Message));
        }
    }
    public async ValueTask<AddSubscriptionResponse> SubscribeAsync(AddSubscriptionRequest request, CancellationToken cancellationToken = default)
    {
        try
        {
            await _gatewayRegistry.SubscribeAsync(request).ConfigureAwait(true);
            return new AddSubscriptionResponse { };
        }
        catch (Exception ex)
        {
            throw new RpcException(new Status(StatusCode.Internal, ex.Message));
        }
    }
    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        while (!stoppingToken.IsCancellationRequested)
        {
            try
            {
                await _gatewayRegistry.AddWorkerAsync(_reference);
            }
            catch (Exception exception)
            {
                _logger.LogWarning(exception, "Error adding worker to registry.");
            }
            await Task.Delay(TimeSpan.FromSeconds(15), stoppingToken);
        }
        try
        {
            await _gatewayRegistry.RemoveWorkerAsync(_reference);
        }
        catch (Exception exception)
        {
            _logger.LogWarning(exception, "Error removing worker from registry.");
        }
    }
    internal async Task ConnectToWorkerProcess(IAsyncStreamReader<Message> requestStream, IServerStreamWriter<Message> responseStream, ServerCallContext context)
    {
        _logger.LogInformation("Received new connection from {Peer}.", context.Peer);
        var clientId = (context.RequestHeaders.Get("client-id")?.Value) ??
            throw new RpcException(new Status(StatusCode.InvalidArgument, "Client ID is required."));
        var workerProcess = new GrpcWorkerConnection(this, requestStream, responseStream, context);
        _workers.GetOrAdd(clientId, workerProcess);
        await workerProcess.Connect().ConfigureAwait(false);
    }
    internal async Task SendMessageAsync(GrpcWorkerConnection connection, CloudEvent cloudEvent, CancellationToken cancellationToken = default)
    {
        await connection.ResponseStream.WriteAsync(new Message { CloudEvent = cloudEvent }, cancellationToken).ConfigureAwait(false);
    }
    internal async Task OnReceivedMessageAsync(GrpcWorkerConnection connection, Message message, CancellationToken cancellationToken = default)
    {
        _logger.LogInformation("Received message {Message} from connection {Connection}.", message, connection);
        switch (message.MessageCase)
        {
            case Message.MessageOneofCase.Request:
                await DispatchRequestAsync(connection, message.Request);
                break;
            case Message.MessageOneofCase.Response:
                DispatchResponse(connection, message.Response);
                break;
            case Message.MessageOneofCase.CloudEvent:
                await DispatchEventAsync(message.CloudEvent, cancellationToken);
                break;
            default:
                // if it wasn't recognized return bad request
                await RespondBadRequestAsync(connection, $"Unknown message type for message '{message}'.");
                break;
        };
    }
    private void DispatchResponse(GrpcWorkerConnection connection, RpcResponse response)
    {
        if (!_pendingRequests.TryRemove((connection, response.RequestId), out var completion))
        {
            _logger.LogWarning("Received response for unknown request id: {RequestId}.", response.RequestId);
            return;
        }
        // Complete the request.
        completion.SetResult(response);
    }
    private async ValueTask DispatchEventAsync(CloudEvent evt, CancellationToken cancellationToken = default)
    {
        var registry = _clusterClient.GetGrain<IRegistryGrain>(0);
        //intentionally blocking
        var targetAgentTypes = await registry.GetSubscribedAndHandlingAgentsAsync(evt.Source, evt.Type).ConfigureAwait(true);
        if (targetAgentTypes is not null && targetAgentTypes.Count > 0)
        {
            targetAgentTypes = targetAgentTypes.Distinct().ToList();
            var tasks = new List<Task>(targetAgentTypes.Count);
            foreach (var agentType in targetAgentTypes)
            {
                if (_supportedAgentTypes.TryGetValue(agentType, out var connections))
                {
                    // if the connection is alive, add it to the set, if not remove the connection from the list
                    var activeConnections = connections.Where(c => c.Completion?.IsCompleted == false).ToList();
                    foreach (var connection in activeConnections)
                    {
                        tasks.Add(this.SendMessageAsync(connection, evt, cancellationToken));
                    }
                }
            }
        }
        else
        {
            // log that no agent types were found
            _logger.LogWarning("No agent types found for event type {EventType}.", evt.Type);
        }
    }
    private async ValueTask DispatchRequestAsync(GrpcWorkerConnection connection, RpcRequest request)
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
                // TODO// Activate the worker: load state
            }
            // Forward the message to the gateway and return the result.
            return await gateway.InvokeRequestAsync(request).ConfigureAwait(true);
        }).ConfigureAwait(false);
    }
    private static async Task InvokeRequestDelegate(GrpcWorkerConnection connection, RpcRequest request, Func<RpcRequest, Task<RpcResponse>> func)
    {
        try
        {
            var response = await func(request);
            response.RequestId = request.RequestId;
            await connection.ResponseStream.WriteAsync(new Message { Response = response }).ConfigureAwait(false);
        }
        catch (Exception ex)
        {
            await connection.ResponseStream.WriteAsync(new Message { Response = new RpcResponse { RequestId = request.RequestId, Error = ex.Message } }).ConfigureAwait(false);
        }
    }
    internal void OnRemoveWorkerProcess(GrpcWorkerConnection workerProcess)
    {
        var clientId = workerProcess.ServerCallContext.RequestHeaders.Get("client-id")?.Value ??
            throw new RpcException(new Status(StatusCode.InvalidArgument, "Grpc Client ID is required."));
        _workers.TryRemove(clientId, out _);
        var types = workerProcess.GetSupportedTypes();
        foreach (var type in types)
        {
            if (_supportedAgentTypes.TryGetValue(type, out var supported))
            {
                supported.Remove(workerProcess);
            }
        }
        // Any agents activated on that worker are also gone.
        foreach (var pair in _agentDirectory)
        {
            if (pair.Value == workerProcess)
            {
                ((IDictionary<(string Type, string Key), GrpcWorkerConnection>)_agentDirectory).Remove(pair);
            }
        }
    }
    private static async ValueTask RespondBadRequestAsync(GrpcWorkerConnection connection, string error)
    {
        throw new RpcException(new Status(StatusCode.InvalidArgument, error));
    }
    private async ValueTask AddSubscriptionAsync(GrpcWorkerConnection connection, AddSubscriptionRequest request)
    {
        var topic = "";
        var agentType = "";
        if (request.Subscription.TypePrefixSubscription is not null)
        {
            topic = request.Subscription.TypePrefixSubscription.TopicTypePrefix;
            agentType = request.Subscription.TypePrefixSubscription.AgentType;
        }
        else if (request.Subscription.TypeSubscription is not null)
        {
            topic = request.Subscription.TypeSubscription.TopicType;
            agentType = request.Subscription.TypeSubscription.AgentType;
        }
        _subscriptionsByAgentType[agentType] = request.Subscription;
        _subscriptionsByTopic.GetOrAdd(topic, _ => []).Add(agentType);
        await _subscriptions.SubscribeAsync(topic, agentType);
        //var response = new SubscriptionResponse { RequestId = request.RequestId, Error = "", Success = true };
        Message response = new()
        {
            AddSubscriptionResponse = new()
            {
                RequestId = request.RequestId,
                Error = "",
                Success = true
            }
        };
        await connection.ResponseStream.WriteAsync(response).ConfigureAwait(false);
    }
    private async ValueTask DispatchEventToAgentsAsync(IEnumerable<string> agentTypes, CloudEvent evt)
    {
        var tasks = new List<Task>(agentTypes.Count());
        foreach (var agentType in agentTypes)
        {
            if (_supportedAgentTypes.TryGetValue(agentType, out var connections))
            {
                foreach (var connection in connections)
                {
                    tasks.Add(this.SendMessageAsync(connection, evt));
                }
            }
        }
        await Task.WhenAll(tasks).ConfigureAwait(false);
    }
    public async ValueTask BroadcastEventAsync(CloudEvent evt, CancellationToken cancellationToken = default)
    {
        var tasks = new List<Task>(_workers.Count);
        foreach (var (_, connection) in _supportedAgentTypes)
        {

            tasks.Add(this.SendMessageAsync((GrpcWorkerConnection)connection[0], evt, default));
        }
        await Task.WhenAll(tasks).ConfigureAwait(false);
    }
    public async Task SendMessageAsync(GrpcWorkerConnection connection, CloudEvent cloudEvent, CancellationToken cancellationToken = default)
    {
        var queue = (GrpcWorkerConnection)connection;
        await queue.ResponseStream.WriteAsync(new Message { CloudEvent = cloudEvent }, cancellationToken).ConfigureAwait(false);
    }

    public async ValueTask<RemoveSubscriptionResponse> UnsubscribeAsync(RemoveSubscriptionRequest request, CancellationToken cancellationToken = default)
    {
        try
        {
            await _gatewayRegistry.UnsubscribeAsync(request).ConfigureAwait(true);
            return new RemoveSubscriptionResponse { };
        }
        catch (Exception ex)
        {
            throw new RpcException(new Status(StatusCode.Internal, ex.Message));
        }
    }
    public ValueTask<List<Subscription>> GetSubscriptionsAsync(GetSubscriptionsRequest request, CancellationToken cancellationToken = default)
    {
        return _gatewayRegistry.GetSubscriptionsAsync(request);
    }
    async ValueTask<RpcResponse> IGateway.InvokeRequestAsync(RpcRequest request)
    {
        return await InvokeRequestAsync(request, default).ConfigureAwait(false);
    }
    async ValueTask IGateway.BroadcastEventAsync(CloudEvent evt)
    {
        await BroadcastEventAsync(evt, default).ConfigureAwait(false);
    }
    ValueTask IGateway.StoreAsync(AgentState value)
    {
        return StoreAsync(value, default);
    }
    ValueTask<AgentState> IGateway.ReadAsync(Protobuf.AgentId agentId)
    {
        return ReadAsync(agentId, default);
    }
    ValueTask<RegisterAgentTypeResponse> IGateway.RegisterAgentTypeAsync(RegisterAgentTypeRequest request, ServerCallContext context)
    {
        return RegisterAgentTypeAsync(request, context, default);
    }
    ValueTask<AddSubscriptionResponse> IGateway.SubscribeAsync(AddSubscriptionRequest request)
    {
        return SubscribeAsync(request, default);
    }
    ValueTask<RemoveSubscriptionResponse> IGateway.UnsubscribeAsync(RemoveSubscriptionRequest request)
    {
        return UnsubscribeAsync(request, default);
    }
    ValueTask<List<Subscription>> IGateway.GetSubscriptionsAsync(GetSubscriptionsRequest request)
    {
        return GetSubscriptionsAsync(request);
    }
}
