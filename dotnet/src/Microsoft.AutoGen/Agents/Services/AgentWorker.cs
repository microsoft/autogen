// Copyright (c) Microsoft Corporation. All rights reserved.
// AgentWorker.cs

using System.Collections.Concurrent;
using System.Diagnostics;
using System.Threading.Channels;
using Microsoft.AutoGen.Abstractions;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;

namespace Microsoft.AutoGen.Agents;

public class AgentWorker :
     IHostedService,
     IAgentWorker
{
    private readonly ConcurrentDictionary<string, Type> _agentTypes = new();
    private readonly ConcurrentDictionary<(string Type, string Key), IAgentBase> _agents = new();
    private readonly ILogger<AgentWorker> _logger;
    private readonly Channel<object> _mailbox = Channel.CreateUnbounded<object>();
    private readonly ConcurrentDictionary<string, AgentState> _agentStates = new();
    private readonly ConcurrentDictionary<string, (IAgentBase Agent, string OriginalRequestId)> _pendingClientRequests = new();
    private readonly CancellationTokenSource _shutdownCts;
    private readonly IServiceProvider _serviceProvider;
    private readonly IEnumerable<Tuple<string, Type>> _configuredAgentTypes;
    private readonly ConcurrentDictionary<string, Subscription> _subscriptionsByAgentType = new();
    private readonly ConcurrentDictionary<string, List<string>> _subscriptionsByTopic = new();
    private readonly DistributedContextPropagator _distributedContextPropagator;
    private readonly CancellationTokenSource _shutdownCancellationToken = new();
    private Task? _mailboxTask;
    private readonly object _channelLock = new();

    public AgentWorker(
    IHostApplicationLifetime hostApplicationLifetime,
    IServiceProvider serviceProvider,
    [FromKeyedServices("AgentTypes")] IEnumerable<Tuple<string, Type>> configuredAgentTypes,
    ILogger<GrpcAgentWorker> logger,
    DistributedContextPropagator distributedContextPropagator)
    {
        _logger = logger;
        _serviceProvider = serviceProvider;
        _configuredAgentTypes = configuredAgentTypes;
        _distributedContextPropagator = distributedContextPropagator;
        _shutdownCts = CancellationTokenSource.CreateLinkedTokenSource(hostApplicationLifetime.ApplicationStopping);
    }
    // this is the in-memory version - we just pass the message directly to the agent(s) that handle this type of event
    public async ValueTask PublishEventAsync(CloudEvent cloudEvent, CancellationToken cancellationToken = default)
    {
        foreach (var (typeName, _) in _agentTypes)
        {
            if (typeName == nameof(Client)) { continue; }
            var agent = GetOrActivateAgent(new AgentId(typeName, cloudEvent.Source));
            agent.ReceiveMessage(new Message { CloudEvent = cloudEvent });
        }
    }
    public async ValueTask SendRequestAsync(IAgentBase agent, RpcRequest request, CancellationToken cancellationToken = default)
    {
        var requestId = Guid.NewGuid().ToString();
        _pendingClientRequests[requestId] = (agent, request.RequestId);
        request.RequestId = requestId;
        await _mailbox.Writer.WriteAsync(request, cancellationToken).ConfigureAwait(false);
    }
    public ValueTask SendResponseAsync(RpcResponse response, CancellationToken cancellationToken = default)
    {
        return _mailbox.Writer.WriteAsync(new Message { Response = response }, cancellationToken);
    }
    public ValueTask SendMessageAsync(Message message, CancellationToken cancellationToken = default)
    {
        return _mailbox.Writer.WriteAsync(message, cancellationToken);
    }
    public ValueTask StoreAsync(AgentState value, CancellationToken cancellationToken = default)
    {
        var agentId = value.AgentId ?? throw new InvalidOperationException("AgentId is required when saving AgentState.");
        // add or update _agentStates with the new state
        var response = _agentStates.AddOrUpdate(agentId.ToString(), value, (key, oldValue) => value);
        return ValueTask.CompletedTask;
    }
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
                    case Message msg when msg.AddSubscriptionRequest != null:
                        await AddSubscriptionRequestAsync(msg.AddSubscriptionRequest).ConfigureAwait(true);
                        break;
                    case Message msg when msg.AddSubscriptionResponse != null:
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
    private async ValueTask AddSubscriptionRequestAsync(AddSubscriptionRequest subscription)
    {
        var topic = subscription.Subscription.TypeSubscription.TopicType;
        var agentType = subscription.Subscription.TypeSubscription.AgentType;
        _subscriptionsByAgentType[agentType] = subscription.Subscription;
        _subscriptionsByTopic.GetOrAdd(topic, _ => []).Add(agentType);
        Message response = new()
        {
            AddSubscriptionResponse = new()
            {
                RequestId = subscription.RequestId,
                Error = "",
                Success = true
            }
        };
        await _mailbox.Writer.WriteAsync(response).ConfigureAwait(false);
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
    private IAgentBase GetOrActivateAgent(AgentId agentId)
    {
        if (!_agents.TryGetValue((agentId.Type, agentId.Key), out var agent))
        {
            if (_agentTypes.TryGetValue(agentId.Type, out var agentType))
            {
                var context = new AgentRuntime(agentId, this, _serviceProvider.GetRequiredService<ILogger<Agent>>(), _distributedContextPropagator);
                agent = (Agent)ActivatorUtilities.CreateInstance(_serviceProvider, agentType, context);
                _agents.TryAdd((agentId.Type, agentId.Key), agent);
            }
            else
            {
                throw new InvalidOperationException($"Agent type '{agentId.Type}' is unknown.");
            }
        }

        return agent;
    }
}
