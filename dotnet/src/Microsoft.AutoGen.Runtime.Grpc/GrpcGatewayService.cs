// Copyright (c) Microsoft Corporation. All rights reserved.
// GrpcGatewayService.cs

using Grpc.Core;
using Microsoft.AutoGen.Contracts;

namespace Microsoft.AutoGen.Runtime.Grpc;

// gRPC service which handles communication between the agent worker and the cluster.
public sealed class GrpcGatewayService : AgentRpc.AgentRpcBase
{
    private readonly GrpcGateway Gateway;
    public GrpcGatewayService(GrpcGateway gateway)
    {
        Gateway = gateway;
    }
    public override async Task OpenChannel(IAsyncStreamReader<Message> requestStream, IServerStreamWriter<Message> responseStream, ServerCallContext context)
    {
        try
        {
           // HACK: check if the request is comming fom our tests, then completes the request
           var shouldComplete = context.Host.StartsWith("AutoGen.Tests");
           await Gateway.ConnectToWorkerProcess(requestStream, responseStream, context, shouldComplete);
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

    public override async Task<SaveStateResponse> SaveState(Contracts.AgentState request, ServerCallContext context)
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
        return await Gateway.AddSubscriptionAsync(request);
    }

    public override async Task<RegisterAgentTypeResponse> RegisterAgent(RegisterAgentTypeRequest request, ServerCallContext context)
    {
        request.RequestId = context.Peer;
        return await Gateway.RegisterAgentTypeAsync(request);
    }
}
