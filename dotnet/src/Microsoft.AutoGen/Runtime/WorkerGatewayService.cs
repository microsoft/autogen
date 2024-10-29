using Grpc.Core;
using Microsoft.AutoGen.Abstractions;

namespace Microsoft.AutoGen.Runtime;

// gRPC service which handles communication between the agent worker and the cluster.
internal sealed class WorkerGatewayService(WorkerGateway agentWorker) : AgentRpc.AgentRpcBase
{
    public override async Task OpenChannel(IAsyncStreamReader<Message> requestStream, IServerStreamWriter<Message> responseStream, ServerCallContext context)
    {
        try
        {
            await agentWorker.ConnectToWorkerProcess(requestStream, responseStream, context).ConfigureAwait(true);
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
        var state = await agentWorker.Read(request);
        return new GetStateResponse { AgentState = state };
    }

    public override async Task<SaveStateResponse> SaveState(AgentState request, ServerCallContext context)
    {
        await agentWorker.Store(request);
        return new SaveStateResponse
        {
            Success = true // TODO: Implement error handling
        };
    }
}
