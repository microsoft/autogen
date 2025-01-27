// Copyright (c) Microsoft Corporation. All rights reserved.
// IAgentRuntime.cs

using Google.Protobuf;
namespace Microsoft.AutoGen.Contracts;

/// <summary>
/// Defines the common surface for agent runtime implementations.
/// </summary>
public interface IAgentRuntime
{
    /// <summary>
    /// Gets the dependency injection service provider for the runtime.
    /// </summary>
    IServiceProvider RuntimeServiceProvider { get; }

    /// <summary>
    /// Registers a new agent type asynchronously.
    /// </summary>
    /// <param name="request">The request containing the agent type details.</param>
    /// <param name="cancellationToken">A token to cancel the operation.</param>
    /// <returns>A task that represents the asynchronous operation.</returns>
    ValueTask RegisterAgentTypeAsync(RegisterAgentTypeRequest request, CancellationToken cancellationToken = default);

    /// <summary>
    /// to be removed in favor of send_message
    /// Sends a request to and agent.
    /// </summary>
    /// <param name="agent">The agent sending the request.</param>
    /// <param name="request">The request to be sent.</param>
    /// <param name="cancellationToken">A token to cancel the operation.</param>
    /// <returns>A task that represents the asynchronous operation.</returns>
    ValueTask RuntimeSendRequestAsync(IAgent agent, RpcRequest request, CancellationToken cancellationToken = default);

    /// <summary>
    /// Sends a response to the above request.
    ///     /// to be removed in favor of send_message
    /// </summary>
    /// <param name="response">The response to be sent.</param>
    /// <param name="cancellationToken">A token to cancel the operation.</param>
    /// <returns>A task that represents the asynchronous operation.</returns>
    ValueTask RuntimeSendResponseAsync(RpcResponse response, CancellationToken cancellationToken = default);

    /// <summary>
    /// Publishes a message to a topic.
    /// </summary>
    /// <param name="message">The message to be published.</param>
    /// <param name="topic">The topic to publish the message to.</param>
    /// <param name="sender">The agent sending the message.</param>
    /// <param name="cancellationToken">A token to cancel the operation.</param>
    /// <returns>A task that represents the asynchronous operation.</returns>
    ValueTask PublishMessageAsync(IMessage message, TopicId topic, IAgent? sender, CancellationToken? cancellationToken = default);

    /// <summary>
    /// Saves the state of an agent asynchronously.
    /// </summary>
    /// <param name="value">The state to be saved.</param>
    /// <param name="cancellationToken">A token to cancel the operation.</param>
    /// <returns>A task that represents the asynchronous operation.</returns>
    ValueTask SaveStateAsync(AgentState value, CancellationToken cancellationToken = default);

    /// <summary>
    /// Loads the state of an agent asynchronously.
    /// </summary>
    /// <param name="agentId">The ID of the agent whose state is to be loaded.</param>
    /// <param name="cancellationToken">A token to cancel the operation.</param>
    /// <returns>A task that represents the asynchronous operation, containing the agent state.</returns>
    ValueTask<AgentState> LoadStateAsync(AgentId agentId, CancellationToken cancellationToken = default);

    /// <summary>
    /// Adds a subscription to a topic.
    /// </summary>
    /// <param name="request">The request containing the subscription types.</param>
    /// <param name="cancellationToken">A token to cancel the operation.</param>
    /// <returns>A task that represents the asynchronous operation, containing the response.</returns>
    ValueTask<AddSubscriptionResponse> AddSubscriptionAsync(AddSubscriptionRequest request, CancellationToken cancellationToken = default);

    /// <summary>
    /// Removes a subscription.
    /// </summary>
    /// <param name="request">The request containing the subscription id.</param>
    /// <param name="cancellationToken">A token to cancel the operation.</param>
    /// <returns>A task that represents the asynchronous operation, containing the response.</returns>
    ValueTask<RemoveSubscriptionResponse> RemoveSubscriptionAsync(RemoveSubscriptionRequest request, CancellationToken cancellationToken = default);

    /// <summary>
    /// Gets the list of subscriptions.
    /// </summary>
    /// <param name="request">The request containing the subscription query details.</param>
    /// <param name="cancellationToken">A token to cancel the operation.</param>
    /// <returns>A task that represents the asynchronous operation, containing the list of subscriptions.</returns>
    ValueTask<List<Subscription>> GetSubscriptionsAsync(GetSubscriptionsRequest request, CancellationToken cancellationToken = default);
}
