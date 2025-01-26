// Copyright (c) Microsoft Corporation. All rights reserved.
// IAgentRuntime.cs

using Google.Protobuf;
using Microsoft.AutoGen.Contracts;
namespace Microsoft.AutoGen.Core;

public interface IAgentRuntime
{
    IServiceProvider RuntimeServiceProvider { get; }
    ValueTask RuntimeSendRequestAsync(Agent agent, RpcRequest request, CancellationToken cancellationToken = default);
    ValueTask RuntimeSendResponseAsync(RpcResponse response, CancellationToken cancellationToken = default);
    ValueTask PublishMessageAsync(IMessage message, TopicId topic, Agent? sender, CancellationToken? cancellationToken = default);
    ValueTask SaveStateAsync(AgentState value, CancellationToken cancellationToken = default);
    ValueTask<AgentState> LoadStateAsync(AgentId agentId, CancellationToken cancellationToken = default);
    ValueTask<AddSubscriptionResponse> AddSubscriptionAsync(AddSubscriptionRequest request, CancellationToken cancellationToken = default);
    ValueTask<RemoveSubscriptionResponse> RemoveSubscriptionAsync(RemoveSubscriptionRequest request, CancellationToken cancellationToken = default);
    ValueTask<List<Subscription>> GetSubscriptionsAsync(GetSubscriptionsRequest request, CancellationToken cancellationToken = default);
}
