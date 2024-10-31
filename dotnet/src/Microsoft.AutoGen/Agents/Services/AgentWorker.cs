// Copyright (c) Microsoft Corporation. All rights reserved.
// AgentWorker.cs

using System.Collections.Concurrent;
using Microsoft.AutoGen.Abstractions;
using Microsoft.Extensions.Logging;

namespace Microsoft.AutoGen.Agents;

public class AgentWorker : IAgentWorker
{
    private readonly ILogger<AgentWorker> _logger;
    private readonly InMemoryQueue<CloudEvent> _eventsQueue = new();
    private readonly InMemoryQueue<Message> _messageQueue = new();
    private readonly ConcurrentDictionary<string, AgentState> _agentStates = new();
    private readonly ConcurrentDictionary<string, (IAgentBase Agent, string OriginalRequestId)> _pendingClientRequests = new();
    public AgentWorker(ILogger<AgentWorker> logger)
    {
        _logger = logger;
    }
    public async ValueTask PublishEventAsync(CloudEvent evt, CancellationToken cancellationToken = default)
    {
        await this.WriteAsync(evt,cancellationToken).ConfigureAwait(false);
    }
    public ValueTask SendRequest(IAgentBase agent, RpcRequest request, CancellationToken cancellationToken = default)
    {
        _logger.LogInformation("[{AgentId}] Sending request '{Request}'.", agent.AgentId, request);
        var requestId = Guid.NewGuid().ToString();
        _pendingClientRequests[requestId] = (agent, request.RequestId);
        request.RequestId = requestId;
        return this.WriteAsync(new Message { Request = request }, cancellationToken);
    }
    public ValueTask SendResponse(RpcResponse response, CancellationToken cancellationToken = default)
    {
        _logger.LogInformation("Sending response '{Response}'.", response);
        return this.WriteAsync(new Message { Response = response }, cancellationToken);
    }
    public ValueTask Store(AgentState value, CancellationToken cancellationToken = default)
    {
        var agentId = value.AgentId ?? throw new InvalidOperationException("AgentId is required when saving AgentState.");
        var response = _agentStates.TryAdd(agentId.ToString(), value);
        if (!response)
        {
            throw new InvalidOperationException($"Error saving AgentState for AgentId {agentId}.");
        }
        return ValueTask.CompletedTask;
    }
    public ValueTask<AgentState> Read(AgentId agentId, CancellationToken cancellationToken = default)
    {
        _agentStates.TryGetValue(agentId.ToString(), out var state);
        //TODO: BUG:if (response.Success && response.AgentState.AgentId is not null) - why is success always false?
        if (state is not null && state.AgentId is not null)
        {
            return new ValueTask<AgentState>(state);
        }
        else
        {
            throw new KeyNotFoundException($"Failed to read AgentState for {agentId}.");
        }
    }
    // In-Memory specific implementations
    private ValueTask WriteAsync(Message message, CancellationToken cancellationToken = default)
    {
        return _messageQueue.Writer.WriteAsync(message, cancellationToken);
    }
    private ValueTask WriteAsync(CloudEvent evt, CancellationToken cancellationToken = default)
    {
        return _eventsQueue.Writer.WriteAsync(evt, cancellationToken);
    }
}
