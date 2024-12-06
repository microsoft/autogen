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
        var connection = _workersByConnection[request.RequestId];
        connection.AddSupportedType(request.Type);
        _supportedAgentTypes.GetOrAdd(request.Type, _ => []).Add(connection);
        _agentsToEventsMap.TryAdd(request.Type, new HashSet<string>(request.Events));

        await _gatewayRegistry.RegisterAgentType(request.Type, _reference).ConfigureAwait(true);
        var response = new RegisterAgentTypeResponse {
        };
        return response;
    }

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
