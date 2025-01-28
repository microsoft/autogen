// Copyright (c) Microsoft Corporation. All rights reserved.
// InProcessRuntime.cs

using System.Collections.Concurrent;
using System.Diagnostics;
using Microsoft.AutoGen.Contracts;
using Microsoft.Extensions.Hosting;

namespace Microsoft.AutoGen.Core;

public sealed class InProcessRuntime : IAgentRuntime, IHostedService
{
    public bool DeliverToSelf { get; set; } //= false;

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

    private ConcurrentQueue<MessageDelivery> messageDeliveryQueue = new();

    private async ValueTask PublishMessageServicer(MessageEnvelope envelope, CancellationToken deliveryToken)
    {
        if (!envelope.Topic.HasValue)
        {
            throw new InvalidOperationException("Message must have a topic to be published.");
        }

        TopicId topic = envelope.Topic.Value;
        foreach (var subscription in this.subscriptions.Values.Where(subscription => subscription.Matches(topic)))
        {
            AgentId? sender = envelope.Sender;

            CancellationTokenSource combinedSource = CancellationTokenSource.CreateLinkedTokenSource(envelope.Cancellation, deliveryToken);
            MessageContext messageContext = new(envelope.MessageId, combinedSource.Token)
            {
                Sender = sender,
                Topic = topic,
                IsRpc = false
            };

            AgentId agentId = subscription.MapToAgent(topic);
            if (!this.DeliverToSelf && sender.HasValue && sender == agentId)
            {
                continue;
            }

            IHostableAgent agent = await this.EnsureAgentAsync(agentId);

            // TODO: Cancellation propagation!
            await agent.OnMessageAsync(envelope.Message, messageContext);
        }
    }

    public ValueTask PublishMessageAsync(object message, TopicId topic, AgentId? sender = null, string? messageId = null, CancellationToken cancellation = default)
    {
        return this.ExecuteTracedAsync(() =>
        {
            MessageDelivery delivery = new MessageEnvelope(message, messageId, cancellation)
                                        .WithSender(sender)
                                        .ForPublish(topic, this.PublishMessageServicer);

            this.messageDeliveryQueue.Enqueue(delivery);

            return ValueTask.CompletedTask;
        });
    }

    private async ValueTask<object?> SendMessageServicer(MessageEnvelope envelope, CancellationToken deliveryToken)
    {
        if (!envelope.Receiver.HasValue)
        {
            throw new InvalidOperationException("Message must have a receiver to be sent.");
        }

        CancellationTokenSource combinedSource = CancellationTokenSource.CreateLinkedTokenSource(envelope.Cancellation, deliveryToken);
        MessageContext messageContext = new(envelope.MessageId, combinedSource.Token)
        {
            Sender = envelope.Sender,
            IsRpc = false
        };

        AgentId receiver = envelope.Receiver.Value;
        IHostableAgent agent = await this.EnsureAgentAsync(receiver);

        return await agent.OnMessageAsync(envelope.Message, messageContext);
    }

    public ValueTask<object?> SendMessageAsync(object message, AgentId recepient, AgentId? sender = null, string? messageId = null, CancellationToken cancellationToken = default)
    {
        return this.ExecuteTracedAsync(() =>
        {
            MessageDelivery delivery = new MessageEnvelope(message, messageId, cancellationToken)
                                            .WithSender(sender)
                                            .ForSend(recepient, this.SendMessageServicer);

            this.messageDeliveryQueue.Enqueue(delivery);
            return delivery.Future;
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
        // Declare the lambda return type explicitly, as otherwise the compiler will infer 'ValueTask<TAgent>'
        // and recurse into the same call, causing a stack overflow.
        => this.RegisterAgentFactoryAsync(type, async ValueTask<IHostableAgent> (agentId, runtime) => await factoryFunc(agentId, runtime));

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

    public ValueTask ProcessNextMessage(CancellationToken cancellation = default)
    {
        Debug.WriteLine("Processing next message...");
        if (this.messageDeliveryQueue.TryDequeue(out MessageDelivery? delivery))
        {
            Debug.WriteLine($"Processing message {delivery.Message.MessageId}...");
            return delivery.InvokeAsync(cancellation);
        }

        return ValueTask.CompletedTask;
    }

    private Func<bool> shouldContinue = () => true;
    private CancellationTokenSource? finishSource;
    private async Task RunAsync(CancellationToken cancellation)
    {
        while (!cancellation.IsCancellationRequested && shouldContinue())
        {
            await this.ProcessNextMessage(cancellation);
        }

        await this.FinishAsync(this.finishSource?.Token ?? CancellationToken.None);
    }

    private CancellationTokenSource? shutdownSource;
    private Task messageDeliveryTask = Task.CompletedTask;
    public ValueTask StartAsync(CancellationToken token = default)
    {
        if (this.shutdownSource != null)
        {
            throw new InvalidOperationException("Runtime is already running.");
        }

        this.shutdownSource = new CancellationTokenSource();
        this.messageDeliveryTask = Task.Run(() => this.RunAsync(this.shutdownSource.Token));

        return ValueTask.CompletedTask;
    }

    public ValueTask StopAsync(CancellationToken token = default)
    {
        if (this.shutdownSource == null)
        {
            throw new InvalidOperationException("Runtime is not running.");
        }

        if (this.finishSource != null)
        {
            // TODO: Log as warning instead?
            throw new InvalidOperationException("Runtime is already stopping.");
        }

        this.finishSource = CancellationTokenSource.CreateLinkedTokenSource(token);

        this.shutdownSource.Cancel();
        this.shutdownSource = null;

        return ValueTask.CompletedTask;
    }

    public Task RunUntilIdleAsync()
    {
        this.shouldContinue = () => !this.messageDeliveryQueue.IsEmpty;

        // TODO: Do we want detach semantics?
        return this.messageDeliveryTask;
    }

    private async Task FinishAsync(CancellationToken token)
    {
        foreach (IHostableAgent agent in this.agentInstances.Values)
        {
            if (!token.IsCancellationRequested)
            {
                await agent.CloseAsync();
            }
        }
    }

    Task IHostedService.StartAsync(CancellationToken cancellationToken) => this.StartAsync(cancellationToken).AsTask();

    Task IHostedService.StopAsync(CancellationToken cancellationToken) => this.StopAsync(cancellationToken).AsTask();
}
