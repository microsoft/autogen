// Copyright (c) Microsoft Corporation. All rights reserved.
// Gateway.cs

using System.Collections.Concurrent;
using Microsoft.AutoGen.Abstractions;
namespace Microsoft.AutoGen.Agents;
// IWorkerGateway in memory implementation
public class InGateway : IGateway
{
    private static readonly TimeSpan s_agentResponseTimeout = TimeSpan.FromSeconds(30);
    private readonly ConcurrentDictionary<string, List<InMemoryQueue<CloudEvent>>> _gatewaySupportedAgentTypes = [];
    private readonly ConcurrentDictionary<(string Type, string Key), InMemoryQueue<CloudEvent>> _agentDirectory = new();
    private readonly ConcurrentDictionary<InMemoryQueue<CloudEvent>, InMemoryQueue<CloudEvent>> _workers = new();
    private readonly ConcurrentDictionary<(InMemoryQueue<Message>, string), TaskCompletionSource<RpcResponse>> _pendingRequests = new();
    private readonly InMemoryQueue<Message> _messageQueue = new();

    public async ValueTask<RpcResponse> InvokeRequest(RpcRequest request, CancellationToken cancellationToken = default)
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
    public async ValueTask BroadcastEvent(CloudEvent evt, CancellationToken cancellationToken = default)
    {
        // TODO: filter the workers that receive the event
        var tasks = new List<Task>(_workers.Count);
        foreach (var (_, connection) in _workers)
        {
            tasks.Add(connection.Writer.WriteAsync(evt).AsTask());
        }
        await Task.WhenAll(tasks).ConfigureAwait(false);
    }
}