// Copyright (c) Microsoft Corporation. All rights reserved.
// IAgentWorker.cs

using Microsoft.AutoGen.Contracts;

namespace Microsoft.AutoGen.Core;

/// <summary>
/// Interface for agent worker operations.
/// </summary>
public interface IAgentWorker
{
    /// <summary>
    /// Publishes a cloud event asynchronously.
    /// </summary>
    /// <param name="evt">The cloud event to publish.</param>
    /// <param name="cancellationToken">A token to cancel the operation.</param>
    /// <returns>A task that represents the asynchronous operation.</returns>
    ValueTask PublishEventAsync(CloudEvent evt, CancellationToken cancellationToken = default);

    /// <summary>
    /// Sends a request asynchronously.
    /// </summary>
    /// <param name="agent">The agent sending the request.</param>
    /// <param name="request">The request to send.</param>
    /// <param name="cancellationToken">A token to cancel the operation.</param>
    /// <returns>A task that represents the asynchronous operation.</returns>
    ValueTask SendRequestAsync(Agent agent, RpcRequest request, CancellationToken cancellationToken = default);

    /// <summary>
    /// Sends a response asynchronously.
    /// </summary>
    /// <param name="response">The response to send.</param>
    /// <param name="cancellationToken">A token to cancel the operation.</param>
    /// <returns>A task that represents the asynchronous operation.</returns>
    ValueTask SendResponseAsync(RpcResponse response, CancellationToken cancellationToken = default);

    /// <summary>
    /// Sends a message asynchronously.
    /// </summary>
    /// <param name="message">The message to send.</param>
    /// <param name="cancellationToken">A token to cancel the operation.</param>
    /// <returns>A task that represents the asynchronous operation.</returns>
    ValueTask SendMessageAsync(Message message, CancellationToken cancellationToken = default);

    /// <summary>
    /// Stores the agent state asynchronously.
    /// </summary>
    /// <param name="value">The agent state to store.</param>
    /// <param name="cancellationToken">A token to cancel the operation.</param>
    /// <returns>A task that represents the asynchronous operation.</returns>
    ValueTask StoreAsync(AgentState value, CancellationToken cancellationToken = default);

    /// <summary>
    /// Reads the agent state asynchronously.
    /// </summary>
    /// <param name="agentId">The ID of the agent whose state is to be read.</param>
    /// <param name="cancellationToken">A token to cancel the operation.</param>
    /// <returns>A task that represents the asynchronous operation, containing the agent state.</returns>
    ValueTask<AgentState> ReadAsync(AgentId agentId, CancellationToken cancellationToken = default);
}
