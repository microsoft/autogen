// Copyright (c) Microsoft Corporation. All rights reserved.
// IGatewayRegistry.cs

using Microsoft.AutoGen.Contracts;

namespace Microsoft.AutoGen.Runtime.Grpc.Abstractions;

/// <summary>
/// Interface for managing agent registration, placement, and subscriptions.
/// </summary>
public interface IGatewayRegistry : IRegistry
{
    /// <summary>
    /// Gets or places an agent based on the provided agent ID.
    /// </summary>
    /// <param name="agentId">The ID of the agent.</param>
    /// <returns>A tuple containing the worker and a boolean indicating if it's a new placement.</returns>
    ValueTask<(IGateway? Worker, bool NewPlacement)> GetOrPlaceAgent(AgentId agentId);

    /// <summary>
    /// Removes a worker from the registry.
    /// </summary>
    /// <param name="worker">The worker to remove.</param>
    /// <returns>A task representing the asynchronous operation.</returns>
    ValueTask RemoveWorkerAsync(IGateway worker);

    /// <summary>
    /// Registers a new agent type with the specified worker.
    /// </summary>
    /// <param name="request">The request containing agent type details.</param>
    /// <param name="worker">The worker to register the agent type with.</param>
    /// <returns>A task representing the asynchronous operation.</returns>
    ValueTask RegisterAgentTypeAsync(RegisterAgentTypeRequest request, IGateway worker);

    /// <summary>
    /// Adds a new worker to the registry.
    /// </summary>
    /// <param name="worker">The worker to add.</param>
    /// <returns>A task representing the asynchronous operation.</returns>
    ValueTask AddWorkerAsync(IGateway worker);

    /// <summary>
    /// Gets a compatible worker for the specified agent type.
    /// </summary>
    /// <param name="type">The type of the agent.</param>
    /// <returns>A task representing the asynchronous operation, with the compatible worker as the result.</returns>
    ValueTask<IGateway?> GetCompatibleWorkerAsync(string type);
}
