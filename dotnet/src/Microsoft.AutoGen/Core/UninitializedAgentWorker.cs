// Copyright (c) Microsoft Corporation. All rights reserved.
// UninitializedAgentWorker.cs

using Google.Protobuf;
using Microsoft.AutoGen.Contracts;

namespace Microsoft.AutoGen.Core;
public class UninitializedAgentWorker() : IAgentRuntime
{
    public IServiceProvider RuntimeServiceProvider => throw new AgentInitalizedIncorrectlyException(AgentNotInitializedMessage);
    internal const string AgentNotInitializedMessage = "Agent not initialized correctly. An Agent should never be directly intialized - it is always started by the AgentWorker from the Runtime (using the static Initialize() method).";
    public ValueTask<AgentState> LoadStateAsync(AgentId agentId, CancellationToken cancellationToken = default) => throw new AgentInitalizedIncorrectlyException(AgentNotInitializedMessage);
    public ValueTask RuntimeSendRequestAsync(Agent agent, RpcRequest request, CancellationToken cancellationToken = default) => throw new AgentInitalizedIncorrectlyException(AgentNotInitializedMessage);
    public ValueTask RuntimeSendResponseAsync(RpcResponse response, CancellationToken cancellationToken = default) => throw new AgentInitalizedIncorrectlyException(AgentNotInitializedMessage);
    public ValueTask SaveStateAsync(AgentState value, CancellationToken cancellationToken = default) => throw new AgentInitalizedIncorrectlyException(AgentNotInitializedMessage);
    public ValueTask<List<Subscription>> GetSubscriptionsAsync(GetSubscriptionsRequest request, CancellationToken cancellationToken = default) => throw new AgentInitalizedIncorrectlyException(AgentNotInitializedMessage);
    public ValueTask<AddSubscriptionResponse> AddSubscriptionAsync(AddSubscriptionRequest request, CancellationToken cancellationToken = default) => throw new AgentInitalizedIncorrectlyException(AgentNotInitializedMessage);
    public ValueTask<RemoveSubscriptionResponse> RemoveSubscriptionAsync(RemoveSubscriptionRequest request, CancellationToken cancellationToken = default) => throw new AgentInitalizedIncorrectlyException(AgentNotInitializedMessage);
    public ValueTask PublishMessageAsync(IMessage message, TopicId topic, Agent? sender, CancellationToken? cancellationToken = null) => throw new AgentInitalizedIncorrectlyException(AgentNotInitializedMessage);
    public class AgentInitalizedIncorrectlyException(string message) : Exception(message)
    {
    }
}
