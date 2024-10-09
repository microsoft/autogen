
using Microsoft.AutoGen.Agents.Abstractions;

namespace Microsoft.AutoGen.Agents.Runtime;

public interface IWorkerGateway : IGrainObserver
{
    ValueTask<RpcResponse> InvokeRequest(RpcRequest request);
    ValueTask BroadcastEvent(CloudEvent evt);
}
