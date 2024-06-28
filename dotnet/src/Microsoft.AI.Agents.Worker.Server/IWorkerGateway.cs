using Agents;
using RpcEvent = Agents.Event;

namespace Microsoft.AI.Agents.Worker;

public interface IWorkerGateway : IGrainObserver
{
    ValueTask<RpcResponse> InvokeRequest(RpcRequest request);
    ValueTask BroadcastEvent(RpcEvent evt);
}
