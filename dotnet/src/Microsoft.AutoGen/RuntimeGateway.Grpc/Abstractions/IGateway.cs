// Copyright (c) Microsoft Corporation. All rights reserved.
// IGateway.cs
using Grpc.Core;
using Microsoft.AutoGen.Protobuf;

namespace Microsoft.AutoGen.RuntimeGateway.Grpc.Abstractions;

public interface IGateway : IGrainObserver
{
    ValueTask<RpcResponse> InvokeRequestAsync(RpcRequest request);
    ValueTask<RegisterAgentTypeResponse> RegisterAgentTypeAsync(RegisterAgentTypeRequest request, ServerCallContext context);
    ValueTask<AddSubscriptionResponse> SubscribeAsync(AddSubscriptionRequest request);
    ValueTask<RemoveSubscriptionResponse> UnsubscribeAsync(RemoveSubscriptionRequest request);
    ValueTask<List<Subscription>> GetSubscriptionsAsync(GetSubscriptionsRequest request);
}
