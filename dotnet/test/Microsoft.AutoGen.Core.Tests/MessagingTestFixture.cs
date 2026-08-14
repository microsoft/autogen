// Copyright (c) Microsoft Corporation. All rights reserved.
// MessagingTestFixture.cs

using Microsoft.AutoGen.Contracts;

namespace Microsoft.AutoGen.Core.Tests;

public sealed class MessagingTestFixture
{
    private Dictionary<Type, object> AgentsTypeMap { get; } = new();
    public InProcessRuntime Runtime { get; private set; } = new();

    public ValueTask<AgentType> RegisterFactoryMapInstances<TAgent>(AgentType type, Func<AgentId, IAgentRuntime, ValueTask<TAgent>> factory)
        where TAgent : IHostableAgent
    {
        Func<AgentId, IAgentRuntime, ValueTask<TAgent>> wrappedFactory = async (id, runtime) =>
        {
            TAgent agent = await factory(id, runtime);
            this.GetAgentInstances<TAgent>()[id] = agent;
            return agent;
        };

        return this.Runtime.RegisterAgentFactoryAsync(type, wrappedFactory);
    }

    public ValueTask RegisterDefaultSubscriptions<TAgentType>(AgentType type) where TAgentType : IHostableAgent
    {
        return this.Runtime.RegisterImplicitAgentSubscriptionsAsync<TAgentType>(type);
    }

    public Dictionary<AgentId, TAgent> GetAgentInstances<TAgent>() where TAgent : IHostableAgent
    {
        if (!AgentsTypeMap.TryGetValue(typeof(TAgent), out object? maybeAgentMap) ||
            maybeAgentMap is not Dictionary<AgentId, TAgent> result)
        {
            this.AgentsTypeMap[typeof(TAgent)] = result = new Dictionary<AgentId, TAgent>();
        }

        return result;
    }

    public async ValueTask<object?> RunSendTestAsync(AgentId sendTarget, object message, string? messageId = null)
    {
        messageId ??= Guid.NewGuid().ToString();

        await this.Runtime.StartAsync();

        object? result = await this.Runtime.SendMessageAsync(message, sendTarget, messageId: messageId);

        await this.Runtime.RunUntilIdleAsync();

        return result;
    }

    public async ValueTask RunPublishTestAsync(TopicId sendTarget, object message, string? messageId = null)
    {
        messageId ??= Guid.NewGuid().ToString();

        await this.Runtime.StartAsync();
        await this.Runtime.PublishMessageAsync(message, sendTarget, messageId: messageId);
        await this.Runtime.RunUntilIdleAsync();
    }
}
