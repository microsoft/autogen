// Copyright (c) Microsoft Corporation. All rights reserved.
// InProcessRuntime.cs

using Microsoft.AutoGen.Contracts;

namespace Microsoft.AutoGen.Core;

public sealed class InProcessRuntime : IAgentRuntime
{
    Dictionary<AgentId, IHostableAgent> agentInstances = new();
    Dictionary<string, ISubscriptionDefinition> subscriptions = new();
    Dictionary<AgentType, Func<AgentId, IAgentRuntime, ValueTask<IHostableAgent>>> agentFactories = new();

    private ValueTask<T> ExecuteTracedAsync<T>(Func<ValueTask<T>> func)
    {
        // TODO: Bind tracing
        return func();
    }

    private ValueTask ExecuteTracedAsync(Func<ValueTask> func)
    {
        // TODO: Bind tracing
        return func();
    }

    public InProcessRuntime()
    {
    }

    public ValueTask PublishMessageAsync(object message, TopicId topic, AgentId? sender = null, string? messageId = null, CancellationToken? cancellationToken = null)
    {
        return this.ExecuteTracedAsync(async () =>
        {
            messageId ??= Guid.NewGuid().ToString();

            foreach (var subscription in this.subscriptions.Values.Where(subscription => subscription.Matches(topic)))
            {
                AgentId agentId = subscription.MapToAgent(topic);
                if (sender.HasValue && sender == agentId)
                {
                    // TODO: enable re-entrant mode
                    continue;
                }

                MessageContext messageContext = new (messageId ?? Guid.NewGuid().ToString(), cancellationToken ?? CancellationToken.None)
                {
                    Sender = sender,
                    Topic = topic,
                    IsRpc = false
                };

                IHostableAgent agent = await this.EnsureAgentAsync(agentId);
                await agent.OnMessageAsync(message, messageContext);
            }
        });
    }

    public ValueTask<object?> SendMessageAsync(object message, AgentId recepient, AgentId? sender = null, string? messageId = null, CancellationToken? cancellationToken = null)
    {
        return this.ExecuteTracedAsync(async () =>
        {
            cancellationToken ??= CancellationToken.None;
            messageId ??= Guid.NewGuid().ToString();

            MessageContext messageContext = new(messageId ?? Guid.NewGuid().ToString(), cancellationToken ?? CancellationToken.None)
            {
                Sender = sender,
                IsRpc = false
            };

            IHostableAgent agent = await this.EnsureAgentAsync(recepient);
            return await agent.OnMessageAsync(message, messageContext);
        });
    }

    private async ValueTask<IHostableAgent> EnsureAgentAsync(AgentId agentId)
    {
        if (!this.agentInstances.TryGetValue(agentId, out IHostableAgent? agent))
        {
            if (!this.agentFactories.TryGetValue(agentId.Type, out Func<AgentId, IAgentRuntime, ValueTask<IHostableAgent>>? factoryFunc))
            {
                throw new Exception($"Agent with name {agentId.Type} not found.");
            }

            agent = await factoryFunc(agentId, this);
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

    public async ValueTask<AgentMetadata> GetAgentMetadataAsync(AgentId agentId)
    {
        IHostableAgent agent = await this.EnsureAgentAsync(agentId);
        return agent.Metadata;
    }

    public async ValueTask LoadAgentStateAsync(AgentId agentId, IDictionary<string, object> state)
    {
        IHostableAgent agent = await this.EnsureAgentAsync(agentId);
        await agent.LoadStateAsync(state);
    }

    public async ValueTask<IDictionary<string, object>> SaveAgentStateAsync(AgentId agentId)
    {
        IHostableAgent agent = await this.EnsureAgentAsync(agentId);
        return await agent.SaveStateAsync();
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

    public async ValueTask LoadStateAsync(IDictionary<string, object> state)
    {
        foreach (var agentIdStr in state.Keys)
        {
            AgentId agentId = AgentId.FromStr(agentIdStr);
            if (state[agentIdStr] is not IDictionary<string, object> agentState)
            {
                throw new Exception($"Agent state for {agentId} is not a {typeof(IDictionary<string, object>)}: {state[agentIdStr].GetType()}");
            }

            if (this.agentFactories.ContainsKey(agentId.Type))
            {
                IHostableAgent agent = await this.EnsureAgentAsync(agentId);
                await agent.LoadStateAsync(agentState);
            }
        }
    }

    public async ValueTask<IDictionary<string, object>> SaveStateAsync()
    {
        Dictionary<string, object> state = new();
        foreach (var agentId in this.agentInstances.Keys)
        {
            state[agentId.ToString()] = await this.agentInstances[agentId].SaveStateAsync();
        }

        return state;
    }

    public ValueTask<AgentType> RegisterAgentFactoryAsync<TAgent>(AgentType type, Func<AgentId, IAgentRuntime, ValueTask<TAgent>> factoryFunc) where TAgent : IHostableAgent
        => this.RegisterAgentFactoryAsync(type, async (agentId, runtime) => await factoryFunc(agentId, runtime));

    public ValueTask<AgentType> RegisterAgentFactoryAsync(AgentType type, Func<AgentId, IAgentRuntime, ValueTask<IHostableAgent>> factoryFunc)
    {
        if (this.agentFactories.ContainsKey(type))
        {
            throw new Exception($"Agent with type {type} already exists.");
        }

        this.agentFactories.Add(type, async (agentId, runtime) => await factoryFunc(agentId, runtime));

        return ValueTask.FromResult(type);
    }

    public ValueTask<AgentProxy> TryGetAgentProxyAsync(AgentId agentId)
    {
        return ValueTask.FromResult(new AgentProxy(agentId, this));
    }
}
