// Copyright (c) Microsoft Corporation. All rights reserved.
// IAgent.cs

using Google.Protobuf;

namespace Microsoft.AutoGen.Contracts;

public interface IAgent
{
    AgentId AgentId { get; }
    IAgentRuntime Worker { get; }
    ValueTask<List<Subscription>> GetSubscriptionsAsync();
    ValueTask<AddSubscriptionResponse> SubscribeAsync(string topic);
    ValueTask<RemoveSubscriptionResponse> UnsubscribeAsync(Guid id);
    ValueTask<RemoveSubscriptionResponse> UnsubscribeAsync(string topic);
    Task StoreAsync(AgentState state, CancellationToken cancellationToken = default);
    Task<T> ReadAsync<T>(AgentId agentId, CancellationToken cancellationToken = default) where T : IMessage, new();
    ValueTask PublishMessageAsync(IMessage message, string topic, string source, string key, CancellationToken token = default);
    ValueTask PublishMessageAsync<T>(T message, string topic, string source, CancellationToken token = default) where T : IMessage;
    ValueTask PublishMessageAsync<T>(T message, string topic, CancellationToken token = default) where T : IMessage;
    ValueTask PublishMessageAsync<T>(T message, CancellationToken token = default) where T : IMessage;
    Task<RpcResponse> HandleRequestAsync(RpcRequest request);
    Task HandleObjectAsync(object item, CancellationToken cancellationToken = default);
}
