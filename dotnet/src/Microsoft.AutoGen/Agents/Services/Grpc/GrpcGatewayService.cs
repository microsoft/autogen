// Copyright (c) Microsoft Corporation. All rights reserved.
// GrpcGatewayService.cs

using Grpc.Core;
using Microsoft.AutoGen.Abstractions;

namespace Microsoft.AutoGen.Agents;

// gRPC service which handles communication between the agent worker and the cluster.
internal sealed class GrpcGatewayService : AgentRpc.AgentRpcBase
{
    private readonly GrpcGateway Gateway;
    public GrpcGatewayService(GrpcGateway gateway)
    {
        Gateway = (GrpcGateway)gateway;
    }
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
}
