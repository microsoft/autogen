// Copyright (c) Microsoft Corporation. All rights reserved.
// InProcessRuntime.cs

using Microsoft.AutoGen.Contracts.Python;

namespace Microsoft.AutoGen.Core;

internal class InProcessRuntime : IAgentRuntime
{
    Dictionary<AgentId, IHostableAgent> agentInstances = new();
    Dictionary<string, ISubscriptionDefinition> subscriptions = new();
    Dictionary<AgentType, Func<AgentId, IAgentRuntime, ValueTask<IHostableAgent>>> agentFactories = new();

    private ValueTask ExecuteTracedAsync<T>(Action<ValueTask<T>> action)
    {
        // TODO: Bind tracing
        return action();
    }

    public InProcessRuntime()
    {
    }

    public ValueTask<object> PublishMessage(object message, TopicId topic, AgentId? sender = null, string? messageId = null, CancellationToken? cancellationToken = null)
    {
        return this.ExecuteTracedAsync(async () =>
        {
            cancellationToken ??= CancellationToken.None;
            messageId ??= Guid.NewGuid().ToString();

            foreach (var subscription in this.subscriptions.Values.Where(subscription => subscription.Matches(topic)))
            {
                AgentId agentId = subscription.MapToAgent(topic);
                if (agentId == sender)
                {
                    // TODO: enable re-entrant mode
                    continue;
                }

                MessageContext messageContext = new MessageContext(messageId)
                {
                    CancellationToken = cancellationToken,
                    Sender = sender,
                    Topic = topic,
                    IsRpc = false
                }

                IHostableAgent agent = await this.EnsureAgentAsync(agentId);
                await agent.OnMessageAsync(message, messageContext);
            }
        });
    }

    public ValueTask<object> SendMessageAsync(object message, AgentId recepient, AgentId? sender = null, string? messageId = null, CancellationToken? cancellationToken = null)
    {
        return this.ExecuteTracedAsync(async () =>
        {
            cancellationToken ??= CancellationToken.None;
            messageId ??= Guid.NewGuid().ToString();

            MessageContext messageContext = new MessageContext(messageId)
            {
                CancellationToken = cancellationToken,
                Sender = sender,
                Topic = topic,
                IsRpc = false
            }

            IHostableAgent agent = await this.EnsureAgentAsync(recepient);
            await agent.OnMessageAsync(message, messageContext);
        });
    }

    private async ValueTask<IHostableAgent> EnsureAgentAsync(AgentId agentId)
    {
        if (!this.agentInstances.ContainsKey(agentId))
        {
            if (!this.agentFactories.ContainsKey(agentId.Type))
            {
                throw new Exception($"Agent with name {agentId.Type} not found.");
            }

            Func<AgentId, IAgentRuntime, ValueTask<IHostableAgent>> factoryFunc = this.agentFactories[agentId.Type]

            var agent = await factoryFunc(agentId, this);

            this.agentInstances.Add(agentId, agent);
        }

        return this.agentInstances[agentId];
    }

    public async ValueTask<AgentId> GetAgentAsync(AgentId agentId, bool lazy = true)
    {
        if (!lazy)
        {
            await this.EnsureAgentAsync(agentId);
        }

        return agentId;
    }

    public ValueTask<AgentId> GetAgentAsync(AgentType agentType, string key = "default", bool lazy = true)
        => this.GetAgentAsync(new AgentId(agentType, key), lazy);

    public ValueTask<AgentId> GetAgentAsync(string agent, string key = "default", bool lazy = true)
        => this.GetAgentAsync(new AgentId(agent, key), lazy);

    public ValueTask<AgentMetadata> GetAgentMetadataAsync(AgentId agentId)
    {
        return this.EnsureAgentAsync(agentId).ContinueWith(agent => agent.Metadata);
    }

    public async ValueTask LoadAgentStateAsync(AgentId agentId, IDictionary<string, object> state)
    {
        IHostableAgent agent = await this.EnsureAgentAsync(agentId);
        await agent.LoadStateAsync(state);
    }

    public ValueTask<IDictionary<string, object>> SaveAgentStateAsync(AgentId agentId)
    {
        IHostableAgent agent = await this.EnsureAgentAsync(agentId);
        return agent.SaveStateAsync();
    }

    /// <inheritdoc cref="IAgentRuntime.AddSubscriptionAsync(ISubscriptionDefinition)"/>
    public ValueTask AddSubscriptionAsync(ISubscriptionDefinition subscription)
    {
        if (this.subscriptions.ContainsKey(subscription.Id))
        {
            throw new Exception($"Subscription with id {subscription.Id} already exists.");
        }

        this.subscriptions.Add(subscription.Id, subscription);
        return ValueTask.CompletedTask;
    }

    public ValueTask RemoveSubscriptionAsync(string subscriptionId)
    {
        if (!this.subscriptions.ContainsKey(subscriptionId))
        {
            throw new Exception($"Subscription with id {subscriptionId} does not exist.");
        }

        this.subscriptions.Remove(subscriptionId);
        return ValueTask.CompletedTask;
    }

    public ValueTask LoadStateAsync(IDictionary<string, object> state)
    {
        foreach (var agentIdStr in state.Keys)
        {
            AgentId agentId = AgentId.FromString(agentIdStr);
            if (this.agentFactories.ContainsKey(agentId.Type))
            {
                await this.EnsureAgentAsync(agentId).LoadStateAsync(state[agentIdStr]);
            }
        }
    }

    public ValueTask<IDictionary<string, object>> SaveStateAsync()
    {
        Dictionary<string, object> state = new();
        foreach (var agentId in this.agentInstances.Keys)
        {
            state[agentId.ToString()] = await this.agentInstances[agentId].SaveStateAsync();
        }
    }

    public ValueTask<AgentType> RegisterAgentFactoryAsync<TAgent>(AgentType type, Func<ValueTask<TAgent>> factoryFunc) where TAgent : IHostableAgent
    {
        if (this.agentFactories.ContainsKey(type))
        {
            throw new Exception($"Agent with type {type} already exists.");
        }

        return type;
    }

    public ValueTask<IAgent> TryGetAgentProxyAsync(AgentId agentId)
    {
        return ValueTask.FromResult(new AgentProxy(agentId, this));
    }
}
