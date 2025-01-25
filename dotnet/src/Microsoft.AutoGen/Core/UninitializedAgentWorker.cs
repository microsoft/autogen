// Copyright (c) Microsoft Corporation. All rights reserved.
// UninitializedAgentWorker.cs

using Microsoft.AutoGen.Contracts;

namespace Microsoft.AutoGen.Core;
public class UninitializedAgentWorker() : IAgentWorker
{
    public IServiceProvider ServiceProvider => throw new AgentInitalizedIncorrectlyException(AgentNotInitializedMessage);
    internal const string AgentNotInitializedMessage = "Agent not initialized correctly. An Agent should never be directly intialized - it is always started by the AgentWorker from the Runtime (using the static Initialize() method).";
    public ValueTask PublishEventAsync(CloudEvent evt, CancellationToken cancellationToken = default) => throw new AgentInitalizedIncorrectlyException(AgentNotInitializedMessage);
    public ValueTask<AgentState> ReadAsync(AgentId agentId, CancellationToken cancellationToken = default) => throw new AgentInitalizedIncorrectlyException(AgentNotInitializedMessage);
    public ValueTask SendMessageAsync(Message message, CancellationToken cancellationToken = default) => throw new AgentInitalizedIncorrectlyException(AgentNotInitializedMessage);
    public ValueTask SendRequestAsync(Agent agent, RpcRequest request, CancellationToken cancellationToken = default) => throw new AgentInitalizedIncorrectlyException(AgentNotInitializedMessage);
    public ValueTask SendResponseAsync(RpcResponse response, CancellationToken cancellationToken = default) => throw new AgentInitalizedIncorrectlyException(AgentNotInitializedMessage);
    public ValueTask StoreAsync(AgentState value, CancellationToken cancellationToken = default) => throw new AgentInitalizedIncorrectlyException(AgentNotInitializedMessage);
    public ValueTask<List<Subscription>> GetSubscriptionsAsync(Type type) => throw new AgentInitalizedIncorrectlyException(AgentNotInitializedMessage);
    public ValueTask<List<Subscription>> GetSubscriptionsAsync(GetSubscriptionsRequest request, CancellationToken cancellationToken = default) => throw new AgentInitalizedIncorrectlyException(AgentNotInitializedMessage);
    public ValueTask<AddSubscriptionResponse> SubscribeAsync(AddSubscriptionRequest request, CancellationToken cancellationToken = default) => throw new AgentInitalizedIncorrectlyException(AgentNotInitializedMessage);
    public ValueTask<RemoveSubscriptionResponse> UnsubscribeAsync(RemoveSubscriptionRequest request, CancellationToken cancellationToken = default) => throw new AgentInitalizedIncorrectlyException(AgentNotInitializedMessage);
    public class AgentInitalizedIncorrectlyException(string message) : Exception(message)
    {
    }
}
