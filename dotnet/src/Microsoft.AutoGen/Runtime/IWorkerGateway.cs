// Copyright (c) Microsoft. All rights reserved.

using Microsoft.AutoGen.Abstractions;

namespace Microsoft.AutoGen.Runtime;

public interface IWorkerGateway : IGrainObserver
{
    ValueTask<RpcResponse> InvokeRequest(RpcRequest request);
    ValueTask BroadcastEvent(CloudEvent evt);
}
