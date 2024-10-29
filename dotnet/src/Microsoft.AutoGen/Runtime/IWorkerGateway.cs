
using Microsoft.AutoGen.Abstractions;

namespace Microsoft.AutoGen.Runtime;

public interface IWorkerGateway : IGrainObserver
{
    ValueTask<RpcResponse> InvokeRequest(RpcRequest request);
    ValueTask BroadcastEvent(CloudEvent evt);
    ValueTask Store(AgentState value);
    ValueTask<AgentState> Read(AgentId agentId);
}
