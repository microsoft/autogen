// Copyright (c) Microsoft Corporation. All rights reserved.
// GrpcGatewayService.cs

using Grpc.Core;
using Microsoft.AutoGen.Contracts;

namespace Microsoft.AutoGen.Runtime.Grpc;

// gRPC service which handles communication between the agent worker and the cluster.
public sealed class GrpcGatewayService(GrpcGateway gateway) : AgentRpc.AgentRpcBase
{
    private readonly GrpcGateway Gateway = (GrpcGateway)gateway;

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
    public override async Task<GetStateResponse> GetState(AgentId request, ServerCallContext context)
    {
        var state = await Gateway.ReadAsync(request);
        return new GetStateResponse { AgentState = state };
    }
    public override async Task<SaveStateResponse> SaveState(AgentState request, ServerCallContext context)
    {
        await Gateway.StoreAsync(request);
        return new SaveStateResponse
        {
            Success = true // TODO: Implement error handling
        };
    }
    public override async Task<AddSubscriptionResponse> AddSubscription(AddSubscriptionRequest request, ServerCallContext context)
    {
        request.RequestId = context.Peer;
        return await Gateway.SubscribeAsync(request).ConfigureAwait(true);
    }
    public override async Task<RemoveSubscriptionResponse> RemoveSubscription(RemoveSubscriptionRequest request, ServerCallContext context)
    {
        return await Gateway.UnsubscribeAsync(request).ConfigureAwait(true);
    }
    public override async Task<GetSubscriptionsResponse> GetSubscriptions(GetSubscriptionsRequest request, ServerCallContext context)
    {
        var subscriptions = await Gateway.GetSubscriptionsAsync(request);
        return new GetSubscriptionsResponse { Subscriptions = { subscriptions } };
    }
    public override async Task<RegisterAgentTypeResponse> RegisterAgent(RegisterAgentTypeRequest request, ServerCallContext context)
    {
        request.RequestId = context.Peer;
        return await Gateway.RegisterAgentTypeAsync(request).ConfigureAwait(true);
    }
}
