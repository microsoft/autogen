// Copyright (c) Microsoft. All rights reserved.

using Microsoft.AutoGen.Abstractions;

namespace Microsoft.AutoGen.Agents;
public interface IAgentWorkerRuntime
{
    ValueTask PublishEvent(CloudEvent evt);
    ValueTask SendRequest(RpcRequest request);
    ValueTask SendResponse(RpcResponse response);
}
