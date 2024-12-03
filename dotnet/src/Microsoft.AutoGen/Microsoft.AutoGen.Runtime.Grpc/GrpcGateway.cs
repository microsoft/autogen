// Copyright (c) Microsoft Corporation. All rights reserved.
// GrpcGateway.cs

using System.Collections.Concurrent;
using Grpc.Core;
using Microsoft.AutoGen.Abstractions;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;

namespace Microsoft.AutoGen.Runtime.Grpc;

public sealed class GrpcGateway : BackgroundService, IGateway
{
    private static readonly TimeSpan s_agentResponseTimeout = TimeSpan.FromSeconds(30);
    private readonly ILogger<GrpcGateway> _logger;
    private readonly IClusterClient _clusterClient;
    private readonly IRegistryGrain _gatewayRegistry;
    private readonly IGateway _reference;

    // The agents supported by each worker process.
    private readonly ConcurrentDictionary<string, List<GrpcWorkerConnection>> _supportedAgentTypes = [];
    internal readonly ConcurrentDictionary<GrpcWorkerConnection, GrpcWorkerConnection> _workers = new();
    internal readonly ConcurrentDictionary<string, GrpcWorkerConnection> _workersByConnection = new();
    private readonly ConcurrentDictionary<string, HashSet<string>> _agentsToEventsMap = new();

    // The mapping from agent id to worker process.
    private readonly ConcurrentDictionary<(string Type, string Key), GrpcWorkerConnection> _agentDirectory = new();
    // RPC
    private readonly ConcurrentDictionary<(GrpcWorkerConnection, string), TaskCompletionSource<RpcResponse>> _pendingRequests = new();

    public int WorkersCount => _workers.Count;

    // InMemory Message Queue

    public GrpcGateway(IClusterClient clusterClient, ILogger<GrpcGateway> logger)
    {
        _logger = logger;
        _clusterClient = clusterClient;
        _reference = clusterClient.CreateObjectReference<IGateway>(this);
        _gatewayRegistry = clusterClient.GetGrain<IRegistryGrain>(0);
    }
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

    internal async Task<string> ConnectToWorkerProcess(IAsyncStreamReader<Message> requestStream, IServerStreamWriter<Message> responseStream, ServerCallContext context)
    {
        _logger.LogInformation("Received new connection from {Peer}.", context.Peer);
        var workerProcess = new GrpcWorkerConnection(this, requestStream, responseStream, context);
        var connectionId = Guid.NewGuid().ToString();
        _workers[workerProcess] = workerProcess;
        _workersByConnection[connectionId] = workerProcess;

        var completion = new TaskCompletionSource<Task>();
        var _ = Task.Run(() =>
        {
            completion.SetResult(workerProcess.Connect());
        });
        
        await completion.Task;
        return connectionId;
    }

    public async ValueTask BroadcastEvent(CloudEvent evt)
    {
        var tasks = new List<Task>();
        foreach (var (key, connection) in _supportedAgentTypes)
        {
            if (_agentsToEventsMap.TryGetValue(key, out var events) && events.Contains(evt.Type))
            {
                tasks.Add(SendMessageAsync(connection[0], evt, default));
            }
        }
        await Task.WhenAll(tasks).ConfigureAwait(false);
    }
    //intetionally not static so can be called by some methods implemented in base class
    internal async Task SendMessageAsync(GrpcWorkerConnection connection, CloudEvent cloudEvent, CancellationToken cancellationToken = default)
    {
        await connection.ResponseStream.WriteAsync(new Message { CloudEvent = cloudEvent }, cancellationToken).ConfigureAwait(false);
    }
    internal async Task OnReceivedMessageAsync(GrpcWorkerConnection connection, Message message)
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
                await DispatchEventAsync(message.CloudEvent);
                break;
            default:
                throw new RpcException(new Status(StatusCode.InvalidArgument, $"Unknown message type for message '{message}'."));
        };
    }
    private void DispatchResponse(GrpcWorkerConnection connection, RpcResponse response)
    {
        if (!_pendingRequests.TryRemove((connection, response.RequestId), out var completion))
        {
            _logger.LogWarning("Received response for unknown request.");
            return;
        }
        // Complete the request.
        completion.SetResult(response);
    }

<<<<<<< HEAD:dotnet/src/Microsoft.AutoGen/Microsoft.AutoGen.Runtime.Grpc/GrpcGateway.cs
=======
    // agentype:rpc_request={requesting_agent_id}
    // {genttype}:rpc_response={request_id}
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
        //var response = new AddSubscriptionResponse { RequestId = request.RequestId, Error = "", Success = true };
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
    private async ValueTask RegisterAgentTypeAsync(GrpcWorkerConnection connection, RegisterAgentTypeRequest msg)
    {
        connection.AddSupportedType(msg.Type);
        _supportedAgentTypes.GetOrAdd(msg.Type, _ => []).Add(connection);

        await _gatewayRegistry.RegisterAgentType(msg.Type, _reference).ConfigureAwait(true);
        Message response = new()
        {
            RegisterAgentTypeResponse = new()
            {
                RequestId = msg.RequestId,
                Error = "",
                Success = true
            }
        };
        await connection.ResponseStream.WriteAsync(response).ConfigureAwait(false);
    }
    private async ValueTask DispatchEventAsync(CloudEvent evt)
    {
        // get the event type and then send to all agents that are subscribed to that event type
        var eventType = evt.Type;
        // ensure that we get agentTypes as an async enumerable list - try to get the value of agentTypes by topic and then cast it to an async enumerable list
        if (_subscriptionsByTopic.TryGetValue(eventType, out var agentTypes))
        {
            await DispatchEventToAgentsAsync(agentTypes, evt);
        }
        // instead of an exact match, we can also check for a prefix match where key starts with the eventType
        else if (_subscriptionsByTopic.Keys.Any(key => key.StartsWith(eventType)))
        {
            _subscriptionsByTopic.Where(
                kvp => kvp.Key.StartsWith(eventType))
                .SelectMany(kvp => kvp.Value)
                .Distinct()
                .ToList()
                .ForEach(async agentType =>
                {
                    await DispatchEventToAgentsAsync(new List<string> { agentType }, evt).ConfigureAwait(false);
                });
        }
        else
        {
            // log that no agent types were found
            _logger.LogWarning("No agent types found for event type {EventType}.", eventType);
        }
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
>>>>>>> 79c5aaa1 (WriteAsync must be awaited (#4491)):dotnet/src/Microsoft.AutoGen/Agents/Services/Grpc/GrpcGateway.cs
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
            return await gateway.InvokeRequest(request).ConfigureAwait(true);
        });
        //}
    }

    private async ValueTask DispatchEventAsync(CloudEvent evt)
    {
        await BroadcastEvent(evt).ConfigureAwait(false);
        /*
        var topic = _clusterClient.GetStreamProvider("agents").GetStream<Event>(StreamId.Create(evt.Namespace, evt.Type));
        await topic.OnNextAsync(evt.ToEvent());
        */
    }

    public async ValueTask<RegisterAgentTypeResponse> RegisterAgentTypeAsync(RegisterAgentTypeRequest request)
    {
        try
        {
            var connection = _workersByConnection[request.RequestId];
            connection.AddSupportedType(request.Type);
            _supportedAgentTypes.GetOrAdd(request.Type, _ => []).Add(connection);
            _agentsToEventsMap.TryAdd(request.Type, new HashSet<string>(request.Events));

            await _gatewayRegistry.RegisterAgentType(request.Type, _reference).ConfigureAwait(true);
            return new RegisterAgentTypeResponse
            {
                Success = true,
                RequestId = request.RequestId
            };
        }
        catch (Exception ex)
        {
            return new RegisterAgentTypeResponse
            {
                Success = false,
                RequestId = request.RequestId,
                Error = ex.Message
            };
        }
    }

    // TODO: consider adding this back for backwards compatibility
    //private async ValueTask RegisterAgentTypeAsync(GrpcWorkerConnection connection, RegisterAgentTypeRequest msg)
    //{

    //}

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

    public async ValueTask StoreAsync(AgentState value)
    {
        var agentState = _clusterClient.GetGrain<IAgentGrain>($"{value.AgentId.Type}:{value.AgentId.Key}");
        await agentState.WriteStateAsync(value, value.ETag);
    }

    public async ValueTask<AgentState> ReadAsync(AgentId agentId)
    {
        var agentState = _clusterClient.GetGrain<IAgentGrain>($"{agentId.Type}:{agentId.Key}");
        return await agentState.ReadStateAsync();
    }

    internal void OnRemoveWorkerProcess(GrpcWorkerConnection workerProcess)
    {
        _workers.TryRemove(workerProcess, out _);
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

    public async ValueTask<RpcResponse> InvokeRequest(RpcRequest request, CancellationToken cancellationToken = default)
    {
        var agentId = (request.Target.Type, request.Target.Key);
        if (!_agentDirectory.TryGetValue(agentId, out var connection) || connection.Completion?.IsCompleted == true)
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

   

    public ValueTask<RpcResponse> InvokeRequest(RpcRequest request)
    {
        throw new NotImplementedException();
    }
}
