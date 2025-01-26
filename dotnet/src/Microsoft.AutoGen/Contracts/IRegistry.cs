// Copyright (c) Microsoft Corporation. All rights reserved.
// IRegistry.cs
namespace Microsoft.AutoGen.Contracts;

public interface IRegistry
{
    AgentsRegistryState State { get; set; }
    /// <summary>
    /// Registers a new agent type with the specified worker.
    /// </summary>
    /// <param name="request">The request containing agent type details.</param>
    /// <param name="worker">The worker to register the agent type with.</param>
    /// <returns>A task representing the asynchronous operation.</returns>
    ValueTask RegisterAgentTypeAsync(RegisterAgentTypeRequest request, IAgentRuntime worker, CancellationToken cancellationToken = default);

    /// <summary>
    /// Unregisters an agent type from the specified worker.
    /// </summary>
    /// <param name="type">The type of the agent to unregister.</param>
    /// <param name="worker">The worker to unregister the agent type from.</param>
    /// <returns>A task representing the asynchronous operation.</returns>
    ValueTask UnregisterAgentTypeAsync(string type, IAgentRuntime worker, CancellationToken cancellationToken = default);

    /// <summary>
    /// Gets a list of agents subscribed to and handling the specified topic and event type.
    /// </summary>
    /// <param name="topic">The topic to check subscriptions for.</param>
    /// <param name="eventType">The event type to check subscriptions for.</param>
    /// <returns>A task representing the asynchronous operation, with the list of agent IDs as the result.</returns>
    ValueTask<List<string>> GetSubscribedAndHandlingAgentsAsync(string topic, string eventType, CancellationToken cancellationToken = default);

    /// <summary>
    /// Subscribes an agent to a topic.
    /// </summary>
    /// <param name="request">The subscription request.</param>
    /// <returns>A task representing the asynchronous operation.</returns>
    ValueTask SubscribeAsync(AddSubscriptionRequest request, CancellationToken cancellationToken = default);

    /// <summary>
    /// Unsubscribes an agent from a topic.
    /// </summary>
    /// <param name="request">The unsubscription request.</param>
    /// <returns>A task representing the asynchronous operation.</returns>
    ValueTask UnsubscribeAsync(RemoveSubscriptionRequest request, CancellationToken cancellationToken = default); // TODO: This should have its own request type.

    /// <summary>
    /// Gets the subscriptions for a specified agent type.
    /// </summary>
    /// <returns>A task representing the asynchronous operation, with the subscriptions as the result.</returns>
    ValueTask<List<Subscription>> GetSubscriptionsAsync(GetSubscriptionsRequest request, CancellationToken cancellationToken = default);
}