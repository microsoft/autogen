// Copyright (c) Microsoft Corporation. All rights reserved.
// IGateway.cs
using Microsoft.AutoGen.Contracts;

namespace Microsoft.AutoGen.Runtime.Grpc;

public interface IGateway : IGrainObserver
{
    ValueTask<RpcResponse> InvokeRequest(RpcRequest request);
    ValueTask BroadcastEvent(CloudEvent evt);
    ValueTask StoreAsync(AgentState value);
    ValueTask<AgentState> ReadAsync(AgentId agentId);
    Task SendMessageAsync(IConnection connection, CloudEvent cloudEvent);
}
