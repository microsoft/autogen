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
    /// <summary>
    /// The Orleans cluster client.
    /// </summary>
    private readonly IClusterClient _clusterClient;
    /// <summary>
    /// The Orleans Grain that manages the AgentRegistration, Subscription, and Gateways
    /// </summary>
    private readonly IRegistryGrain _gatewayRegistry;
    /// <summary>
    /// The Orleans Grain that manages the DeadLetterQueue and MessageBuffer
    /// </summary>
    private readonly IMessageRegistryGrain _messageRegistry;
    private readonly IGateway _reference;
    private readonly ConcurrentDictionary<string, List<GrpcWorkerConnection<Message>>> _supportedAgentTypes = [];
    public readonly ConcurrentDictionary<string, GrpcWorkerConnection<Message>> _workers = new();
    public readonly ConcurrentDictionary<string, GrpcWorkerConnection<ControlMessage>> _controlWorkers = new();
    private readonly ConcurrentDictionary<(string Type, string Key), GrpcWorkerConnection<Message>> _agentDirectory = new();
    private readonly ConcurrentDictionary<(GrpcWorkerConnection<Message>, string), TaskCompletionSource<RpcResponse>> _pendingRequests = new();

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

            Func<ValueTask> registerLambda = async () =>
            {
                if (!_workers.TryGetValue(clientId, out var connection))
                {
                    throw new RpcException(new Status(StatusCode.InvalidArgument, $"Grpc Worker Connection not found for ClientId {clientId}. Retry after you call OpenChannel() first."));
                }
                connection.AddSupportedType(request.Type);
                _supportedAgentTypes.GetOrAdd(request.Type, _ => []).Add(connection);

                await _gatewayRegistry.RegisterAgentTypeAsync(request, clientId, _reference).ConfigureAwait(true);
            };

            await InvokeOrDeferRegistrationAction(clientId, registerLambda).ConfigureAwait(true);

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
            // We do not actually need to defer these, since we do not listen to ClientId on this for some reason...
            // TODO: Fix this
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
                    _logger.LogInformation("Removed {Count} dead-letter and buffer messages for topic '{Topic}'.", removedMessages.Count, topic);
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
            // We do not need to defer here because we will never have a guid to send to this unless the deferred
            // AddSubscription calls were run after a client connection was established.
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
    internal async Task ConnectToWorkerProcess<TMessage>(IAsyncStreamReader<TMessage> requestStream, IServerStreamWriter<TMessage> responseStream, ServerCallContext context)
    where TMessage : class
    {
        _logger.LogInformation("Received new connection from {Peer}.", context.Peer);
        var clientId = context.RequestHeaders.Get("client-id")?.Value
            ?? throw new RpcException(new Status(StatusCode.InvalidArgument, "Client ID is required."));
        var workerProcess = new GrpcWorkerConnection<TMessage>(this, requestStream, responseStream, context);

        if (typeof(TMessage) == typeof(Message))
        {
            _workers.GetOrAdd(clientId, _ => (GrpcWorkerConnection<Message>)(object)workerProcess);
            await this.AttachDanglingRegistrations(clientId).ConfigureAwait(false);
        }
        else if (typeof(TMessage) == typeof(ControlMessage))
        {
            _controlWorkers.GetOrAdd(clientId, _ => (GrpcWorkerConnection<ControlMessage>)(object)workerProcess);
        }
        else
        {
            throw new InvalidOperationException($"Unsupported message type: {typeof(TMessage).Name}");
        }

        await workerProcess.Connect().ConfigureAwait(false);
    }

    private ConcurrentDictionary<string, ConcurrentQueue<Func<ValueTask>>> _danglingRequests = new();
    private async Task InvokeOrDeferRegistrationAction(string clientId, Func<ValueTask> action)
    {
        if (_workers.TryGetValue(clientId, out var _))
        {
            await action().ConfigureAwait(false);
        }
        else
        {
            ConcurrentQueue<Func<ValueTask>> danglingRequestQueue = _danglingRequests.GetOrAdd(clientId, _ => new ConcurrentQueue<Func<ValueTask>>());
            danglingRequestQueue.Enqueue(action);
        }
    }

    private async Task AttachDanglingRegistrations(string clientId)
    {
        _logger.LogInformation("Attaching dangling registrations for {ClientId}.", clientId);
        if (_danglingRequests.TryRemove(clientId, out var requests))
        {
            foreach (var request in requests)
            {
                await request().ConfigureAwait(false);
            }
        }
    }

    /// <summary>
    /// Handles received messages from a worker connection.
    /// </summary>
    /// <param name="connection">The worker connection.</param>
    /// <param name="message">The received message.</param>
    /// <param name="cancellationToken">The cancellation token.</param>
    /// <returns>A task that represents the asynchronous operation.</returns>
    internal async Task OnReceivedMessageAsync<TMessage>(GrpcWorkerConnection<TMessage> connection, TMessage message, CancellationToken cancellationToken = default)
    where TMessage : class
    {
        _logger.LogInformation("Received message {Message} from connection {Connection}.", message, connection);

        switch (message)
        {
            case Message msg:
                // Handle regular messages
                switch (msg.MessageCase)
                {
                    case Message.MessageOneofCase.Request:
                        await DispatchRequestAsync(connection, msg.Request);
                        break;
                    case Message.MessageOneofCase.Response:
                        DispatchResponse(connection, msg.Response);
                        break;
                    case Message.MessageOneofCase.CloudEvent:
                        await DispatchEventAsync(msg.CloudEvent, cancellationToken);
                        break;
                    default:
                        await RespondBadRequestAsync(connection, $"Unknown message type for message '{msg}'.");
                        break;
                }
                break;

            case ControlMessage controlMsg:
                // Handle control messages
                await DispatchControlMessageAsync(connection, controlMsg, cancellationToken);
                break;

            default:
                await RespondBadRequestAsync(connection, $"Unsupported message type: {typeof(TMessage).Name}");
                break;
        }
    }

    /// <summary>
    /// Dispatches a response to a pending request.
    /// </summary>
    /// <param name="connection">The worker connection.</param>
    /// <param name="response">The RPC response.</param>
    private void DispatchResponse<TMessage>(GrpcWorkerConnection<TMessage> connection, RpcResponse response)
    where TMessage : class
    {
        if (connection is GrpcWorkerConnection<Message> messageConnection)
        {
            if (!_pendingRequests.TryRemove((messageConnection, response.RequestId), out var completion))
            {
                _logger.LogWarning("Received response for unknown request id: {RequestId}.", response.RequestId);
                return;
            }
            completion.SetResult(response);
        }
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
                if (_supportedAgentTypes.TryGetValue(agentType, out var connections))
                {
                    // if the connection is alive, add it to the set, if not remove the connection from the list
                    var activeConnections = connections.Where(c => c.Completion?.IsCompleted == false).ToList();
                    foreach (var connection in activeConnections)
                    {
                        _logger.LogDebug("Dispatching event {Event} to connection {Connection}, for AgentType {AgentType}.", evt, connection, agentType);
                        tasks.Add(Task.Run(async () =>
                        {
                            await this.WriteResponseAsync(connection, evt, cancellationToken);
                            await _messageRegistry.AddMessageToEventBufferAsync(evt.Source, evt).ConfigureAwait(true);
                        }));
                    }
                }
                else
                {
                    // we have target agent types that aren't in the supported agent types
                    // could be a race condition or a bug
                    _logger.LogWarning($"Agent type {agentType} is not supported, but registry returned it as subscribed to {evt.Type}/{evt.Source}. Buffering an event to the dead-letter queue.");
                    await _messageRegistry.AddMessageToDeadLetterQueueAsync(evt.Source, evt).ConfigureAwait(true);
                }
            }
            await Task.WhenAll(tasks).ConfigureAwait(false);
        }
        else
        {
            // log that no agent types were found
            _logger.LogWarning("No agent types found for event type {EventType}. Adding to Dead Letter Queue", evt.Type);
            // buffer the event to the dead-letter queue
            await _messageRegistry.AddMessageToDeadLetterQueueAsync(evt.Source, evt).ConfigureAwait(true);
        }
    }

    /// <summary>
    /// Dispatches a request to the appropriate agent.
    /// </summary>
    /// <param name="connection">The worker connection.</param>
    /// <param name="request">The RPC request.</param>
    /// <returns>A task that represents the asynchronous operation.</returns>
    private async ValueTask DispatchRequestAsync<TMessage>(GrpcWorkerConnection<TMessage> connection, RpcRequest request)
    where TMessage : class
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
    private static async Task InvokeRequestDelegate<TMessage>(GrpcWorkerConnection<TMessage> connection, RpcRequest request, Func<RpcRequest, Task<RpcResponse>> func)
    where TMessage : class
    {
        try
        {
            var response = await func(request);
            response.RequestId = request.RequestId;

            if (connection is GrpcWorkerConnection<Message> messageConnection)
            {
                await messageConnection.ResponseStream.WriteAsync(new Message { Response = response }).ConfigureAwait(false);
            }
        }
        catch (Exception ex)
        {
            if (connection is GrpcWorkerConnection<Message> messageConnection)
            {
                await messageConnection.ResponseStream.WriteAsync(
                    new Message { Response = new RpcResponse { RequestId = request.RequestId, Error = ex.Message } }
                ).ConfigureAwait(false);
            }
        }
    }

    /// <summary>
    /// Handles the removal of a worker process.
    /// </summary>
    /// <param name="workerProcess">The worker process.</param>
    internal void OnRemoveWorkerProcess<TMessage>(GrpcWorkerConnection<TMessage> workerProcess)
    where TMessage : class
    {
        var clientId = workerProcess.ServerCallContext.RequestHeaders.Get("client-id")?.Value
            ?? throw new RpcException(new Status(StatusCode.InvalidArgument, "Grpc Client ID is required."));

        _workers.TryRemove(clientId, out _);
        _controlWorkers.TryRemove(clientId, out _);

        var types = workerProcess.GetSupportedTypes();
        foreach (var type in types)
        {
            if (_supportedAgentTypes.TryGetValue(type, out var supported) && workerProcess is GrpcWorkerConnection<Message> messageWorker)
            {
                supported.Remove(messageWorker);
            }
        }

        if (workerProcess is GrpcWorkerConnection<Message> messageWorkerInstance)
        {
            foreach (var pair in _agentDirectory.ToList())
            {
                if (ReferenceEquals(pair.Value, messageWorkerInstance)) // Ensures exact instance match
                {
                    _agentDirectory.TryRemove(pair.Key, out _);
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
    private static async ValueTask RespondBadRequestAsync<TMessage>(GrpcWorkerConnection<TMessage> connection, string error)
    where TMessage : class
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
    private async Task WriteResponseAsync(GrpcWorkerConnection<Message> connection, CloudEvent cloudEvent, CancellationToken cancellationToken = default)
    {
        await connection.ResponseStream.WriteAsync(new Message { CloudEvent = cloudEvent }, cancellationToken).ConfigureAwait(false);
    }

    private async ValueTask DispatchControlMessageAsync<TMessage>(GrpcWorkerConnection<TMessage> connection, ControlMessage controlMsg, CancellationToken cancellationToken)
    where TMessage : class
    {
        if (string.IsNullOrEmpty(controlMsg.Destination))
        {
            throw new InvalidOperationException($"Control message is missing a destination. Message: '{controlMsg}'");
        }

        // Ensure the control message is of the correct type
        if (controlMsg is TMessage typedResponseMessage)
        {
            // Send the response back to the client
            await connection.ResponseStream.WriteAsync(typedResponseMessage, cancellationToken).ConfigureAwait(false);
        }
        else
        {
            throw new InvalidOperationException($"Cannot convert control message to type {typeof(TMessage).Name}");
        }
    }
}
