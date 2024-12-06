// Copyright (c) Microsoft Corporation. All rights reserved.
// GrpcGatewayService.cs

using Grpc.Core;
using Microsoft.AutoGen.Abstractions;

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
            var connectionId = await Gateway.ConnectToWorkerProcess(requestStream, responseStream, context).ConfigureAwait(true);
            // Generate a response with the connectionId, to be used in subsequent RPC requests to the service
            await responseStream.WriteAsync(new Message { Response = new RpcResponse { RequestId = connectionId } });
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

    public override Task<AddSubscriptionResponse> AddSubscription(AddSubscriptionRequest request, ServerCallContext context)
    {
        // TODO: This should map to Orleans Streaming explicit api
        return base.AddSubscription(request, context);
    }

    public override async Task<RegisterAgentTypeResponse> RegisterAgent(RegisterAgentTypeRequest request, ServerCallContext context)
    {
        // TODO: This should add the agent to registry
        return await Gateway.RegisterAgentTypeAsync(request);
    }
}
