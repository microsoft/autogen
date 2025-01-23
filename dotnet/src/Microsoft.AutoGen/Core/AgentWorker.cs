// Copyright (c) Microsoft Corporation. All rights reserved.
// AgentWorker.cs

using System.Collections.Concurrent;
using System.Threading.Channels;
using Microsoft.AutoGen.Contracts;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;

namespace Microsoft.AutoGen.Core;

/// <summary>
/// Represents a worker that manages agents and handles messages.
/// </summary>
/// <remarks>
/// Initializes a new instance of the <see cref="AgentWorker"/> class.
/// </remarks>
/// <param name="hostApplicationLifetime">The application lifetime.</param>
/// <param name="serviceProvider">The service provider.</param>
/// <param name="configuredAgentTypes">The configured agent types.</param>
public class AgentWorker(
    IHostApplicationLifetime hostApplicationLifetime,
    IServiceProvider serviceProvider,
    [FromKeyedServices("AgentTypes")] IEnumerable<Tuple<string, Type>> configuredAgentTypes) : IHostedService, IAgentWorker
{
    private readonly ConcurrentDictionary<string, Type> _agentTypes = new();
    private readonly ConcurrentDictionary<(string Type, string Key), Agent> _agents = new();
    private readonly Channel<object> _mailbox = Channel.CreateUnbounded<object>();
    private readonly ConcurrentDictionary<string, AgentState> _agentStates = new();
    private readonly ConcurrentDictionary<string, (Agent Agent, string OriginalRequestId)> _pendingClientRequests = new();
    private readonly CancellationTokenSource _shutdownCts = CancellationTokenSource.CreateLinkedTokenSource(hostApplicationLifetime.ApplicationStopping);
    public IServiceProvider ServiceProvider { get; } = serviceProvider;
    private readonly IEnumerable<Tuple<string, Type>> _configuredAgentTypes = configuredAgentTypes;
    private readonly ConcurrentDictionary<string, List<Subscription>> _subscriptionsByAgentType = new();
    private readonly ConcurrentDictionary<string, List<string>> _subscriptionsByTopic = new();
    private readonly CancellationTokenSource _shutdownCancellationToken = new();
    private Task? _mailboxTask;
    private readonly object _channelLock = new();

    /// <inheritdoc />
    public async ValueTask PublishEventAsync(CloudEvent cloudEvent, CancellationToken cancellationToken = default)
    {
        foreach (var (typeName, _) in _agentTypes)
        {
            if (typeName == nameof(Client)) { continue; }
            var agent = GetOrActivateAgent(new AgentId { Type = typeName, Key = cloudEvent.GetSubject() });
            agent.ReceiveMessage(new Message { CloudEvent = cloudEvent });
        }
    }

    /// <inheritdoc />
    public async ValueTask SendRequestAsync(Agent agent, RpcRequest request, CancellationToken cancellationToken = default)
    {
        var requestId = Guid.NewGuid().ToString();
        _pendingClientRequests[requestId] = (agent, request.RequestId);
        request.RequestId = requestId;
        await _mailbox.Writer.WriteAsync(request, cancellationToken).ConfigureAwait(false);
    }

    /// <inheritdoc />
    public ValueTask SendResponseAsync(RpcResponse response, CancellationToken cancellationToken = default)
    {
        return _mailbox.Writer.WriteAsync(new Message { Response = response }, cancellationToken);
    }

    /// <inheritdoc />
    public ValueTask SendMessageAsync(Message message, CancellationToken cancellationToken = default)
    {
        return _mailbox.Writer.WriteAsync(message, cancellationToken);
    }

    /// <inheritdoc />
    public ValueTask StoreAsync(AgentState value, CancellationToken cancellationToken = default)
    {
        var agentId = value.AgentId ?? throw new InvalidOperationException("AgentId is required when saving AgentState.");
        var response = _agentStates.AddOrUpdate(agentId.ToString(), value, (key, oldValue) => value);
        return ValueTask.CompletedTask;
    }

    /// <inheritdoc />
    public ValueTask<AgentState> ReadAsync(AgentId agentId, CancellationToken cancellationToken = default)
    {
        _agentStates.TryGetValue(agentId.ToString(), out var state);
        if (state is not null && state.AgentId is not null)
        {
            return new ValueTask<AgentState>(state);
        }
        else
        {
            throw new KeyNotFoundException($"Failed to read AgentState for {agentId}.");
        }
    }

    /// <summary>
    /// Runs the message pump.
    /// </summary>
    public async Task RunMessagePump()
    {
        await Task.CompletedTask.ConfigureAwait(ConfigureAwaitOptions.ForceYielding);
        await foreach (var message in _mailbox.Reader.ReadAllAsync())
        {
            try
            {
                if (message == null) { continue; }
                switch (message)
                {
                    case Message msg when msg.CloudEvent != null:

                        var item = msg.CloudEvent;

                        foreach (var (typeName, _) in _agentTypes)
                        {
                            var agentToInvoke = GetOrActivateAgent(new AgentId(typeName, item.Source));
                            agentToInvoke.ReceiveMessage(msg);
                        }
                        break;
                    case Message msg when msg.SubscriptionRequest != null:
                        await SubscribeAsync(msg.SubscriptionRequest).ConfigureAwait(true);
                        break;
                    case Message msg when msg.SubscriptionResponse != null:
                        break;
                    case Message msg when msg.RegisterAgentTypeResponse != null:
                        break;
                    default:
                        throw new InvalidOperationException($"Unexpected message '{message}'.");
                }
            }
            catch (OperationCanceledException)
            {
            }
            finally
            {
                _shutdownCancellationToken.Cancel();
            }
        }
    }
    public async ValueTask<SubscriptionResponse> SubscribeAsync(SubscriptionRequest subscription, CancellationToken cancellationToken = default)
    {
        var topic = subscription.Subscription.TypeSubscription.TopicType;
        var agentType = subscription.Subscription.TypeSubscription.AgentType;
        _subscriptionsByAgentType.GetOrAdd(key: agentType, _ => []).Add(subscription.Subscription);
        _subscriptionsByTopic.GetOrAdd(topic, _ => []).Add(agentType);
        var response = new SubscriptionResponse
        {
            RequestId = subscription.RequestId,
            Error = "",
            Success = true
        };
        return response;
    }
    public async ValueTask<SubscriptionResponse> UnsubscribeAsync(SubscriptionRequest request, CancellationToken cancellationToken = default)
    {
        var topic = request.Subscription.TypeSubscription.TopicType;
        var agentType = request.Subscription.TypeSubscription.AgentType;
        if (_subscriptionsByAgentType.TryGetValue(agentType, out var subscriptions))
        {
            while (subscriptions.Remove(request.Subscription))
            {
                //ensures all instances are removed    
            }
        }
        if (_subscriptionsByTopic.TryGetValue(topic, out var agentTypes))
        {
            while (agentTypes.Remove(agentType))
            {
                //ensures all instances are removed
            }
        }
        var response = new SubscriptionResponse
        {
            RequestId = request.RequestId,
            Error = "",
            Success = true
        };
        return response;
    }

    public async Task StartAsync(CancellationToken cancellationToken)
    {
        StartCore();

        foreach (var (typeName, type) in _configuredAgentTypes)
        {
            _agentTypes.TryAdd(typeName, type);
        }
        void StartCore()
        {
            var didSuppress = false;
            if (!ExecutionContext.IsFlowSuppressed())
            {
                didSuppress = true;
                ExecutionContext.SuppressFlow();
            }

            try
            {
                _mailboxTask = Task.Run(RunMessagePump, CancellationToken.None);
            }
            finally
            {
                if (didSuppress)
                {
                    ExecutionContext.RestoreFlow();
                }
            }
        }
    }

    /// <inheritdoc />
    public async Task StopAsync(CancellationToken cancellationToken)
    {
        _shutdownCts.Cancel();

        _mailbox.Writer.TryComplete();

        if (_mailboxTask is { } readTask)
        {
            await readTask.ConfigureAwait(false);
        }
        lock (_channelLock)
        {
        }
    }

    /// <summary>
    /// Gets or activates an agent.
    /// </summary>
    /// <param name="agentId">The agent ID.</param>
    /// <returns>The activated agent.</returns>

    private Agent GetOrActivateAgent(AgentId agentId)
    {
        if (!_agents.TryGetValue((agentId.Type, agentId.Key), out var agent))
        {
            if (_agentTypes.TryGetValue(agentId.Type, out var agentType))
            {
                using (var scope = ServiceProvider.CreateScope())
                {
                    var scopedProvider = scope.ServiceProvider;
                    agent = (Agent)ActivatorUtilities.CreateInstance(scopedProvider, agentType);
                    Agent.Initialize(this, agent);
                    _agents.TryAdd((agentId.Type, agentId.Key), agent);
                }
            }
            else
            {
                throw new InvalidOperationException($"Agent type '{agentId.Type}' is unknown.");
            }
        }

        return agent;
    }

    public ValueTask<List<Subscription>> GetSubscriptionsAsync(Type type)
    {
        if (_subscriptionsByAgentType.TryGetValue(type.Name, out var subscriptions))
        {
            return new ValueTask<List<Subscription>>(subscriptions);
        }
        return new ValueTask<List<Subscription>>([]);
    }
}
