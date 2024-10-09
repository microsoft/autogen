// Copyright (c) Microsoft. All rights reserved.

using Microsoft.AutoGen.Agents.Abstractions;

namespace Microsoft.AutoGen.Agents.Client;
public interface IAgentWorkerRuntime
{
    ValueTask PublishEvent(CloudEvent evt);
    ValueTask SendRequest(RpcRequest request);
    ValueTask SendResponse(RpcResponse response);
}
