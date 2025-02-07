// Copyright (c) Microsoft Corporation. All rights reserved.
// IRegistry.cs
using Microsoft.AutoGen.Protobuf;
namespace Microsoft.AutoGen.RuntimeGateway.Grpc.Abstractions;

public interface IRegistry
{

    /// <summary>
    /// Gets a list of agents subscribed to and handling the specified topic and event type.
    /// </summary>
    /// <param name="topic">The topic to check subscriptions for.</param>
    /// <param name="key">The event type to check subscriptions for.</param>
    /// <returns>A task representing the asynchronous operation, with the list of agent IDs as the result.</returns>
    ValueTask<List<string>> GetSubscribedAndHandlingAgentsAsync(string topic, string key);

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
