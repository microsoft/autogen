using Grpc.Core;
using Microsoft.AutoGen.Abstractions;

namespace Microsoft.AutoGen.Runtime;

// gRPC service which handles communication between the agent worker and the cluster.
internal sealed class WorkerGatewayService(WorkerGateway agentWorker) : AgentRpc.AgentRpcBase
{
    public override async Task OpenChannel(IAsyncStreamReader<Message> requestStream, IServerStreamWriter<Message> responseStream, ServerCallContext context)
    {
        await agentWorker.ConnectToWorkerProcess(requestStream, responseStream, context);
    }
}
