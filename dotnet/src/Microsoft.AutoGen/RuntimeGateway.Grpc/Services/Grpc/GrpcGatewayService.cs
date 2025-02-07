// Copyright (c) Microsoft Corporation. All rights reserved.
// GrpcGatewayService.cs
using Grpc.Core;
using Microsoft.AutoGen.Protobuf;

namespace Microsoft.AutoGen.RuntimeGateway.Grpc;

/// <summary>
/// Represents the gRPC service which handles communication between the agent worker and the cluster.
/// </summary>
public sealed class GrpcGatewayService(GrpcGateway gateway) : AgentRpc.AgentRpcBase
{
    private readonly GrpcGateway Gateway = (GrpcGateway)gateway;

    /// <summary>
    /// Method run on first connect from a worker process.
    /// </summary>
    /// <param name="requestStream">The request stream.</param>
    /// <param name="responseStream">The response stream.</param>
    /// <param name="context">The server call context.</param>
    /// <returns>A task that represents the asynchronous operation.</returns>
    public override async Task OpenChannel(IAsyncStreamReader<Message> requestStream, IServerStreamWriter<Message> responseStream, ServerCallContext context)
    {
        try
        {
            await Gateway.ConnectToWorkerProcess(requestStream, responseStream, context).ConfigureAwait(true);
        }
        catch
        {
            if (context.CancellationToken.IsCancellationRequested)
            {
                return;
            }
            throw;
        }
    }

    /// <summary>
    /// Adds a subscription.
    /// </summary>
    /// <param name="request">The add subscription request.</param>
    /// <param name="context">The server call context.</param>
    /// <returns>A task that represents the asynchronous operation. The task result contains the add subscription response.</returns>
    public override async Task<AddSubscriptionResponse> AddSubscription(AddSubscriptionRequest request, ServerCallContext context)
    {
        try
        {
            return await Gateway.SubscribeAsync(request).ConfigureAwait(true);
        }
        catch (Exception e)
        {
            throw new RpcException(new Status(StatusCode.Internal, e.Message));
        }
    }

    /// <summary>
    /// Removes a subscription.
    /// </summary>
    /// <param name="request">The remove subscription request.</param>
    /// <param name="context">The server call context.</param>
    /// <returns>A task that represents the asynchronous operation. The task result contains the remove subscription response.</returns>
    public override async Task<RemoveSubscriptionResponse> RemoveSubscription(RemoveSubscriptionRequest request, ServerCallContext context)
    {
        try
        {
            return await Gateway.UnsubscribeAsync(request).ConfigureAwait(true);
        }
        catch (Exception e)
        {
            throw new RpcException(new Status(StatusCode.Internal, e.Message));
        }
    }

    /// <summary>
    /// Gets the subscriptions.
    /// </summary>
    /// <param name="request">The get subscriptions request.</param>
    /// <param name="context">The server call context.</param>
    /// <returns>A task that represents the asynchronous operation. The task result contains the get subscriptions response.</returns>
    public override async Task<GetSubscriptionsResponse> GetSubscriptions(GetSubscriptionsRequest request, ServerCallContext context)
    {
        try
        {
            var subscriptions = await Gateway.GetSubscriptionsAsync(request);
            return new GetSubscriptionsResponse { Subscriptions = { subscriptions } };
        }
        catch (Exception e)
        {
            throw new RpcException(new Status(StatusCode.Internal, e.Message));
        }
    }

    /// <summary>
    /// Registers an agent type (factory)
    /// </summary>
    /// <param name="request">The register agent type request.</param>
    /// <param name="context">The server call context.</param>
    /// <returns>A task that represents the asynchronous operation. The task result contains the register agent type response.</returns>
    public override async Task<RegisterAgentTypeResponse> RegisterAgent(RegisterAgentTypeRequest request, ServerCallContext context)
    {
        try
        {
            return await Gateway.RegisterAgentTypeAsync(request, context).ConfigureAwait(true);
        }
        catch (Exception e)
        {
            throw new RpcException(new Status(StatusCode.Internal, e.Message));
        }
    }
}
