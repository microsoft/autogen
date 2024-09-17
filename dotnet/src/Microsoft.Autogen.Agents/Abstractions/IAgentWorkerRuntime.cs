// Copyright (c) Microsoft. All rights reserved.

using Agents;

namespace Microsoft.AI.Agents.Worker.Client;
public interface IAgentWorkerRuntime
{
    ValueTask PublishEvent(CloudEvent evt);
    ValueTask SendRequest(RpcRequest request);
    ValueTask SendResponse(RpcResponse response);
}
