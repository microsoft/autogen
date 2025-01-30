// Copyright (c) Microsoft Corporation. All rights reserved.
// IGatewayRegistry.cs

using Microsoft.AutoGen.Contracts;
using Microsoft.AutoGen.Protobuf;

namespace Microsoft.AutoGen.Runtime.Grpc.Abstractions;

public interface IRegistry
{
    //AgentsRegistryState State { get; set; }
    /// <summary>
    /// Registers a new agent type with the specified worker.
    /// </summary>
    /// <param name="request">The request containing agent type details.</param>
    /// <param name="worker">The worker to register the agent type with.</param>
    /// <returns>A task representing the asynchronous operation.</returns>
    /// <remarks>removing CancellationToken from here as it is not compatible with Orleans Serialization</remarks>
    ValueTask RegisterAgentTypeAsync(RegisterAgentTypeRequest request, IAgentRuntime worker);

    /// <summary>
    /// Unregisters an agent type from the specified worker.
    /// </summary>
    /// <param name="type">The type of the agent to unregister.</param>
    /// <param name="worker">The worker to unregister the agent type from.</param>
    /// <returns>A task representing the asynchronous operation.</returns>
    /// <remarks>removing CancellationToken from here as it is not compatible with Orleans Serialization</remarks>
    ValueTask UnregisterAgentTypeAsync(string type, IAgentRuntime worker);

    /// <summary>
    /// Gets a list of agents subscribed to and handling the specified topic and event type.
    /// </summary>
    /// <param name="topic">The topic to check subscriptions for.</param>
    /// <param name="eventType">The event type to check subscriptions for.</param>
    /// <returns>A task representing the asynchronous operation, with the list of agent IDs as the result.</returns>
    ValueTask<List<string>> GetSubscribedAndHandlingAgentsAsync(string topic, string eventType);

    /// <summary>
    /// Subscribes an agent to a topic.
    /// </summary>
    /// <param name="request">The subscription request.</param>
    /// <returns>A task representing the asynchronous operation.</returns>
    /// <remarks>removing CancellationToken from here as it is not compatible with Orleans Serialization</remarks>
    ValueTask SubscribeAsync(AddSubscriptionRequest request);

    /// <summary>
    /// Unsubscribes an agent from a topic.
    /// </summary>
    /// <param name="request">The unsubscription request.</param>
    /// <returns>A task representing the asynchronous operation.</returns>
    /// <remarks>removing CancellationToken from here as it is not compatible with Orleans Serialization</remarks>
    ValueTask UnsubscribeAsync(RemoveSubscriptionRequest request); // TODO: This should have its own request type.

    /// <summary>
    /// Gets the subscriptions for a specified agent type.
    /// </summary>
    /// <returns>A task representing the asynchronous operation, with the subscriptions as the result.</returns>
    ValueTask<List<Subscription>> GetSubscriptionsAsync(GetSubscriptionsRequest request);
}

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
    ValueTask<(IGateway? Worker, bool NewPlacement)> GetOrPlaceAgent(Protobuf.AgentId agentId);

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
