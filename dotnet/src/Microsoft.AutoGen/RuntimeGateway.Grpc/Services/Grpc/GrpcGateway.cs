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

/// <summary>
/// Represents the gRPC gateway service that handles communication between the agent worker and the cluster.
/// </summary>
public sealed class GrpcGateway : BackgroundService, IGateway
{
    private static readonly TimeSpan s_agentResponseTimeout = TimeSpan.FromSeconds(30);
    private readonly ILogger<GrpcGateway> _logger;
    private readonly IClusterClient _clusterClient;
    private readonly IRegistryGrain _gatewayRegistry;
    private readonly IMessageRegistryGrain _messageRegistry;
    private readonly IGateway _reference;
    /// <summary>
    /// dictionary of supported agent types by type and clientid - use clientid to look up the worker
    /// </summary>
    private readonly ConcurrentDictionary<string, string> _supportedAgentTypes = [];
    /// <summary>
    /// dictionary of worker connections by clientid
    /// </summary>
    public readonly ConcurrentDictionary<string, GrpcWorkerConnection> _workers = new();
    private readonly ConcurrentDictionary<(string Type, string Key), GrpcWorkerConnection> _agentDirectory = new();
    private readonly ConcurrentDictionary<(GrpcWorkerConnection, string), TaskCompletionSource<RpcResponse>> _pendingRequests = new();

    /// <summary>
    /// Initializes a new instance of the <see cref="GrpcGateway"/> class.
    /// </summary>
    /// <param name="clusterClient">The cluster client.</param>
    /// <param name="logger">The logger.</param>
    public GrpcGateway(IClusterClient clusterClient, ILogger<GrpcGateway> logger)
    {
        _logger = logger;
        _clusterClient = clusterClient;
        _reference = clusterClient.CreateObjectReference<IGateway>(this);
        _gatewayRegistry = clusterClient.GetGrain<IRegistryGrain>(0);
        _messageRegistry = clusterClient.GetGrain<IMessageRegistryGrain>(0);
    }

    /// <summary>
    /// Executes the background service.
    /// </summary>
    /// <param name="stoppingToken">The cancellation token.</param>
    /// <returns>A task that represents the asynchronous operation.</returns>
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

    /// <summary>
    /// Invokes a request asynchronously.
    /// </summary>
    /// <param name="request">The RPC request.</param>
    /// <param name="cancellationToken">The cancellation token.</param>
    /// <returns>A task that represents the asynchronous operation. The task result contains the RPC response.</returns>
    public async ValueTask<RpcResponse> InvokeRequestAsync(RpcRequest request, CancellationToken cancellationToken = default)
    {
        var agentId = (request.Target.Type, request.Target.Key);
        if (!_agentDirectory.TryGetValue(agentId, out var connection) || connection.Completion.IsCompleted == true)
        {
            if (_supportedAgentTypes.TryGetValue(request.Target.Type, out var supported))
            {
                var clientId = supported;
                if (!_workers.TryGetValue(clientId, out connection))
                {
                    throw new RpcException(new Status(StatusCode.NotFound, $"Worker not found for agent type {request.Target.Type}, clientId {clientId}."));
                }
                _agentDirectory[agentId] = connection;
            }
            else
            {
                return new(new RpcResponse { Error = "Agent not found." });
            }
        }
        var originalRequestId = request.RequestId;
        var newRequestId = Guid.NewGuid().ToString();
        var completion = _pendingRequests[(connection, newRequestId)] = new(TaskCreationOptions.RunContinuationsAsynchronously);
        request.RequestId = newRequestId;
        await connection.ResponseStream.WriteAsync(new Message { Request = request }, cancellationToken).ConfigureAwait(false);
        var response = await completion.Task.WaitAsync(s_agentResponseTimeout);
        response.RequestId = originalRequestId;
        return response;
    }

    /// <summary>
    /// Registers an agent type asynchronously.
    /// </summary>
    /// <param name="request">The register agent type request.</param>
    /// <param name="context">The server call context.</param>
    /// <param name="cancellationToken">The cancellation token.</param>
    /// <returns>A task that represents the asynchronous operation. The task result contains the register agent type response.</returns>
    public async ValueTask<RegisterAgentTypeResponse> RegisterAgentTypeAsync(RegisterAgentTypeRequest request, ServerCallContext context, CancellationToken cancellationToken = default)
    {
        try
        {
            var clientId = context.RequestHeaders.Get("client-id")?.Value ??
                throw new RpcException(new Status(StatusCode.InvalidArgument, "Grpc Client ID is required."));
            if (!_workers.TryGetValue(clientId, out var connection))
            {
                _logger.LogInformation($"Grpc Worker Connection not found for ClientId {clientId}.");
            }
            else { connection.AddSupportedType(request.Type); }
            // we still want to add the supported type - we will bind the connection when it calls OpenChannel
            _supportedAgentTypes.AddOrUpdate(
                request.Type,
                _ => clientId,
                    (_, existing) =>
                        {
                            existing = clientId;
                            return existing;
                        }
                );
            await _gatewayRegistry.RegisterAgentTypeAsync(request, clientId, _reference).ConfigureAwait(true);
            return new RegisterAgentTypeResponse { };
        }
        catch (Exception ex)
        {
            throw new RpcException(new Status(StatusCode.Internal, ex.Message));
        }
    }

    /// <summary>
    /// Subscribes to a topic asynchronously.
    /// </summary>
    /// <param name="request">The add subscription request.</param>
    /// <param name="cancellationToken">The cancellation token.</param>
    /// <returns>A task that represents the asynchronous operation. The task result contains the add subscription response.</returns>
    public async ValueTask<AddSubscriptionResponse> SubscribeAsync(AddSubscriptionRequest request, CancellationToken cancellationToken = default)
    {
        try
        {
            await _gatewayRegistry.SubscribeAsync(request).ConfigureAwait(true);

            var topic = request.Subscription.SubscriptionCase switch
            {
                Subscription.SubscriptionOneofCase.TypeSubscription
                    => request.Subscription.TypeSubscription.TopicType,
                Subscription.SubscriptionOneofCase.TypePrefixSubscription
                    => request.Subscription.TypePrefixSubscription.TopicTypePrefix,
                _ => null
            };

            if (!string.IsNullOrEmpty(topic))
            {
                var removedMessages = await _messageRegistry.RemoveMessagesAsync(topic);
                if (removedMessages.Any())
                {
                    _logger.LogInformation("Removed {Count} dead-letter messages for topic '{Topic}'.", removedMessages.Count, topic);
                    // now that someone is subscribed, dispatch the messages
                    foreach (var message in removedMessages)
                    {
                        await DispatchEventAsync(message).ConfigureAwait(true);
                    }
                }
            }
            return new AddSubscriptionResponse { };
        }
        catch (Exception ex)
        {
            throw new RpcException(new Status(StatusCode.Internal, ex.Message));
        }
    }

    /// <summary>
    /// Unsubscribes from a topic asynchronously.
    /// </summary>
    /// <param name="request">The remove subscription request.</param>
    /// <param name="cancellationToken">The cancellation token.</param>
    /// <returns>A task that represents the asynchronous operation. The task result contains the remove subscription response.</returns>
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

    /// <summary>
    /// Gets the subscriptions asynchronously.
    /// </summary>
    /// <param name="request">The get subscriptions request.</param>
    /// <param name="cancellationToken">The cancellation token.</param>
    /// <returns>A task that represents the asynchronous operation. The task result contains the list of subscriptions.</returns>
    public ValueTask<List<Subscription>> GetSubscriptionsAsync(GetSubscriptionsRequest request, CancellationToken cancellationToken = default)
    {
        return _gatewayRegistry.GetSubscriptionsAsync(request);
    }

    async ValueTask<RpcResponse> IGateway.InvokeRequestAsync(RpcRequest request)
    {
        return await InvokeRequestAsync(request, default).ConfigureAwait(false);
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

    /// <summary>
    /// Connects to a worker process.
    /// </summary>
    /// <param name="requestStream">The request stream.</param>
    /// <param name="responseStream">The response stream.</param>
    /// <param name="context">The server call context.</param>
    /// <returns>A task that represents the asynchronous operation.</returns>
    internal async Task ConnectToWorkerProcess(IAsyncStreamReader<Message> requestStream, IServerStreamWriter<Message> responseStream, ServerCallContext context)
    {
        _logger.LogInformation("Received new connection from {Peer}.", context.Peer);
        var clientId = (context.RequestHeaders.Get("client-id")?.Value) ??
            throw new RpcException(new Status(StatusCode.InvalidArgument, "Client ID is required."));
        var workerProcess = new GrpcWorkerConnection(this, requestStream, responseStream, context);
        _workers.GetOrAdd(clientId, workerProcess);
        await workerProcess.Connect().ConfigureAwait(false);
    }

    /// <summary>
    /// Handles received messages from a worker connection.
    /// </summary>
    /// <param name="connection">The worker connection.</param>
    /// <param name="message">The received message.</param>
    /// <param name="cancellationToken">The cancellation token.</param>
    /// <returns>A task that represents the asynchronous operation.</returns>
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
                await RespondBadRequestAsync(connection, $"Unknown message type for message '{message}'.");
                break;
        }
        ;
    }

    /// <summary>
    /// Dispatches a response to a pending request.
    /// </summary>
    /// <param name="connection">The worker connection.</param>
    /// <param name="response">The RPC response.</param>
    private void DispatchResponse(GrpcWorkerConnection connection, RpcResponse response)
    {
        if (!_pendingRequests.TryRemove((connection, response.RequestId), out var completion))
        {
            _logger.LogWarning("Received response for unknown request id: {RequestId}.", response.RequestId);
            return;
        }
        completion.SetResult(response);
    }

    /// <summary>
    /// Dispatches an event to the appropriate agents.
    /// </summary>
    /// <param name="evt">The cloud event.</param>
    /// <param name="cancellationToken">The cancellation token.</param>
    /// <returns>A task that represents the asynchronous operation.</returns>
    private async ValueTask DispatchEventAsync(CloudEvent evt, CancellationToken cancellationToken = default)
    {
        var registry = _clusterClient.GetGrain<IRegistryGrain>(0);
        //intentionally blocking
        var targetAgentTypes = await registry.GetSubscribedAndHandlingAgentsAsync(evt.Type, evt.Source).ConfigureAwait(true);
        if (targetAgentTypes is not null && targetAgentTypes.Count > 0)
        {
            targetAgentTypes = targetAgentTypes.Distinct().ToList();
            var tasks = new List<Task>(targetAgentTypes.Count);
            foreach (var agentType in targetAgentTypes)
            {
                if (_supportedAgentTypes.TryGetValue(agentType, out var supported))
                {
                    if (supported is null)
                    {
                        _logger.LogWarning("No clientId found for agent type {AgentType}.", agentType);
                        _supportedAgentTypes.TryRemove(agentType, out _);
                        // write to the dead letter queue - maybe it will come back
                        await _messageRegistry.WriteMessageAsync(evt.Source, evt).ConfigureAwait(true);
                        continue;
                    }
                    // check if we can get the worker connection from the _workers dictionary
                    if (_workers.TryGetValue(supported, out var connection))
                    {
                        // is the connection alive?
                        if (connection.Completion?.IsCompleted == false)
                        {
                            tasks.Add(this.WriteResponseAsync(connection, evt, cancellationToken));
                        }
                        else
                        {
                            _logger.LogWarning("Worker connection for agent type {AgentType} is not alive.", agentType);
                            // remove the connection from the list
                            _workers.TryRemove(supported, out _);
                            // remove the agent type from the supported agent types
                            _supportedAgentTypes.TryRemove(agentType, out _);
                            // write to the dead letter queue - maybe it will come back
                            await _messageRegistry.WriteMessageAsync(evt.Source, evt).ConfigureAwait(true);
                        }
                        continue;
                    } // if we can't find the worker connection, write to the dead letter queue
                    _supportedAgentTypes.TryRemove(agentType, out _);
                    // write to the dead letter queue - maybe it will come back
                    await _messageRegistry.WriteMessageAsync(evt.Source, evt).ConfigureAwait(true);
                }
            }
            await Task.WhenAll(tasks).ConfigureAwait(false);
        }
        else
        {
            // log that no agent types were found
            _logger.LogWarning("No agent types found for event type {EventType}.", evt.Type);
            // write to the dead letter queue
            await _messageRegistry.WriteMessageAsync(evt.Source, evt).ConfigureAwait(true);
        }
    }

    /// <summary>
    /// Dispatches a request to the appropriate agent.
    /// </summary>
    /// <param name="connection">The worker connection.</param>
    /// <param name="request">The RPC request.</param>
    /// <returns>A task that represents the asynchronous operation.</returns>
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

    /// <summary>
    /// Invokes a request delegate.
    /// </summary>
    /// <param name="connection">The worker connection.</param>
    /// <param name="request">The RPC request.</param>
    /// <param name="func">The function to invoke.</param>
    /// <returns>A task that represents the asynchronous operation.</returns>
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

    /// <summary>
    /// Handles the removal of a worker process.
    /// </summary>
    /// <param name="workerProcess">The worker process.</param>
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
                if (supported == clientId)
                {
                    _supportedAgentTypes.TryRemove(type, out _);
                }
            }
            foreach (var pair in _agentDirectory)
            {
                if (pair.Value == workerProcess)
                {
                    ((IDictionary<(string Type, string Key), GrpcWorkerConnection>)_agentDirectory).Remove(pair);
                }
            }
        }
    }

    /// <summary>
    /// Responds with a bad request error.
    /// </summary>
    /// <param name="connection">The worker connection.</param>
    /// <param name="error">The error message.</param>
    /// <returns>A task that represents the asynchronous operation.</returns>
    private static async ValueTask RespondBadRequestAsync(GrpcWorkerConnection connection, string error)
    {
        throw new RpcException(new Status(StatusCode.InvalidArgument, error));
    }

    /// <summary>
    /// Writes a response to a worker connection.
    /// </summary>
    /// <param name="connection">The worker connection.</param>
    /// <param name="cloudEvent">The cloud event.</param>
    /// <param name="cancellationToken">The cancellation token.</param>
    /// <returns>A task that represents the asynchronous operation.</returns>
    private async Task WriteResponseAsync(GrpcWorkerConnection connection, CloudEvent cloudEvent, CancellationToken cancellationToken = default)
    {
        await connection.ResponseStream.WriteAsync(new Message { CloudEvent = cloudEvent }, cancellationToken).ConfigureAwait(false);
    }
}
