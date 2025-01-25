// Copyright (c) Microsoft Corporation. All rights reserved.
// IAgentWorker.cs
using Microsoft.AutoGen.Contracts;
namespace Microsoft.AutoGen.Core;

public interface IAgentWorker
{
    IServiceProvider RuntimeServiceProvider { get; }
    ValueTask RuntimePublishEventAsync(CloudEvent evt, CancellationToken cancellationToken = default);
    ValueTask RuntimeSendRequestAsync(Agent agent, RpcRequest request, CancellationToken cancellationToken = default);
    ValueTask RuntimeSendResponseAsync(RpcResponse response, CancellationToken cancellationToken = default);
    ValueTask RuntimeWriteMessage(Message message, CancellationToken cancellationToken = default);
    ValueTask PublishMessageAsync(Message message, CancellationToken cancellationToken = default);
    ValueTask SaveStateAsync(AgentState value, CancellationToken cancellationToken = default);
    ValueTask<AgentState> LoadStateAsync(AgentId agentId, CancellationToken cancellationToken = default);
    ValueTask<AddSubscriptionResponse> AddSubscriptionAsync(AddSubscriptionRequest request, CancellationToken cancellationToken = default);
    ValueTask<RemoveSubscriptionResponse> RemoveSubscriptionAsync(RemoveSubscriptionRequest request, CancellationToken cancellationToken = default);
    ValueTask<List<Subscription>> GetSubscriptionsAsync(GetSubscriptionsRequest request, CancellationToken cancellationToken = default);
}
