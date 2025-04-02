// Copyright (c) Microsoft Corporation. All rights reserved.
// IGateway.cs
using Grpc.Core;
using Microsoft.AutoGen.Protobuf;

namespace Microsoft.AutoGen.RuntimeGateway.Grpc.Abstractions;

/// <summary>
/// Defines the gateway interface for handling RPC requests and subscriptions.
/// Note that all of the request types are generated from the proto file.
/// </summary>
public interface IGateway : IGrainObserver
{
    /// <summary>
    /// Invokes a request asynchronously.
    /// </summary>
    /// <param name="request">The RPC request.</param>
    /// <returns>A task that represents the asynchronous operation. The task result contains the RPC response.</returns>
    ValueTask<RpcResponse> InvokeRequestAsync(RpcRequest request);

    /// <summary>
    /// Registers an agent type asynchronously.
    /// </summary>
    /// <param name="request">The register agent type request.</param>
    /// <param name="context">The server call context.</param>
    /// <returns>A task that represents the asynchronous operation. The task result contains the register agent type response.</returns>
    ValueTask<RegisterAgentTypeResponse> RegisterAgentTypeAsync(RegisterAgentTypeRequest request, ServerCallContext context);

    /// <summary>
    /// Subscribes to a topic asynchronously.
    /// </summary>
    /// <param name="request">The add subscription request.</param>
    /// <returns>A task that represents the asynchronous operation. The task result contains the add subscription response.</returns>
    ValueTask<AddSubscriptionResponse> SubscribeAsync(AddSubscriptionRequest request);

    /// <summary>
    /// Unsubscribes from a topic asynchronously.
    /// </summary>
    /// <param name="request">The remove subscription request.</param>
    /// <returns>A task that represents the asynchronous operation. The task result contains the remove subscription response.</returns>
    ValueTask<RemoveSubscriptionResponse> UnsubscribeAsync(RemoveSubscriptionRequest request);

    /// <summary>
    /// Gets the subscriptions asynchronously.
    /// </summary>
    /// <param name="request">The get subscriptions request.</param>
    /// <returns>A task that represents the asynchronous operation. The task result contains the list of subscriptions.</returns>
    ValueTask<List<Subscription>> GetSubscriptionsAsync(GetSubscriptionsRequest request);
}
