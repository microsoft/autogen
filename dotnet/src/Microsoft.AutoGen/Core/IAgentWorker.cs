// Copyright (c) Microsoft Corporation. All rights reserved.
// IAgentWorker.cs
using Microsoft.AutoGen.Contracts;
namespace Microsoft.AutoGen.Core;

public interface IAgentWorker
{
    IServiceProvider ServiceProvider { get; }
    ValueTask PublishEventAsync(CloudEvent evt, CancellationToken cancellationToken = default);
    ValueTask SendRequestAsync(Agent agent, RpcRequest request, CancellationToken cancellationToken = default);
    ValueTask SendResponseAsync(RpcResponse response, CancellationToken cancellationToken = default);
    ValueTask SendMessageAsync(Message message, CancellationToken cancellationToken = default);
    ValueTask StoreAsync(AgentState value, CancellationToken cancellationToken = default);
    ValueTask<AgentState> ReadAsync(AgentId agentId, CancellationToken cancellationToken = default);
    ValueTask<AddSubscriptionResponse> SubscribeAsync(AddSubscriptionRequest request, CancellationToken cancellationToken = default);
    ValueTask<RemoveSubscriptionResponse> UnsubscribeAsync(RemoveSubscriptionRequest request, CancellationToken cancellationToken = default);
    ValueTask<List<Subscription>> GetSubscriptionsAsync(GetSubscriptionsRequest request, CancellationToken cancellationToken = default);
}
