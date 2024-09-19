using Agents;

namespace Microsoft.AutoGen.Agents.Worker;

public interface IWorkerGateway : IGrainObserver
{
    ValueTask<RpcResponse> InvokeRequest(RpcRequest request);
    ValueTask BroadcastEvent(CloudEvent evt);
}
