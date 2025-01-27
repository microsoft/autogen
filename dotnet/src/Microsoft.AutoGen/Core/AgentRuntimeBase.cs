// Copyright (c) Microsoft Corporation. All rights reserved.
// AgentRuntimeBase.cs

using System.Collections.Concurrent;
using System.Diagnostics;
using System.Threading.Channels;
using Google.Protobuf;
using Microsoft.AutoGen.Contracts;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;

namespace Microsoft.AutoGen.Core;
/// <summary>
/// Base class for agent runtime.
/// </summary>
/// <param name="hostApplicationLifetime">used for shutdown</param>
/// <param name="serviceProvider">the service host for DI container</param>
/// <param name="configuredAgentTypes">the agent types this runtime can host</param>
public abstract class AgentRuntimeBase(
    IHostApplicationLifetime hostApplicationLifetime,
    IServiceProvider serviceProvider,
    [FromKeyedServices("AgentTypes")] IEnumerable<Tuple<string, Type>> configuredAgentTypes) : IHostedService, IAgentRuntime
{
    public IServiceProvider RuntimeServiceProvider { get; } = serviceProvider;
    protected readonly ConcurrentDictionary<string, (Agent Agent, string OriginalRequestId)> _pendingClientRequests = new();
    protected readonly Channel<object> _mailbox = Channel.CreateUnbounded<object>();
    private readonly ConcurrentDictionary<(string Type, string Key), Agent> _agents = new();
    private readonly ConcurrentDictionary<string, Type> _agentTypes = new();
    private readonly CancellationTokenSource _shutdownCts = CancellationTokenSource.CreateLinkedTokenSource(hostApplicationLifetime.ApplicationStopping);
    private readonly CancellationTokenSource _shutdownCancellationToken = new();
    private readonly IEnumerable<Tuple<string, Type>> _configuredAgentTypes = configuredAgentTypes;
    private Task? _mailboxTask;
    private readonly object _channelLock = new();

    /// <summary>
    /// Starts the agent runtime.
    /// Required to implement IHostedService
    /// </summary>
    /// <param name="cancellationToken"></param>
    /// <returns>Task</returns>
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
    /// <summary>
    /// Stops the agent runtime.
    /// Required to implement IHostedService.
    /// </summary>
    /// <param name="cancellationToken"></param>
    /// <returns>Task</returns>
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
                    case Message msg when msg.AddSubscriptionRequest != null:
                        await AddSubscriptionAsync(msg.AddSubscriptionRequest).ConfigureAwait(true);
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
    public async ValueTask PublishMessageAsync(IMessage message, TopicId topic, Agent? sender, CancellationToken? cancellationToken = default)
    {
        var topicString = topic.Type + "." + topic.Source;
        sender ??= RuntimeServiceProvider.GetRequiredService<Client>();
        await PublishEventAsync(message.ToCloudEvent(key: sender.GetType().Name, topic: topicString), sender, cancellationToken.GetValueOrDefault()).ConfigureAwait(false);
    }
    public abstract ValueTask SaveStateAsync(AgentState value, CancellationToken cancellationToken = default);
    public abstract ValueTask<AgentState> LoadStateAsync(AgentId agentId, CancellationToken cancellationToken = default);
    public abstract ValueTask<AddSubscriptionResponse> AddSubscriptionAsync(AddSubscriptionRequest request, CancellationToken cancellationToken = default);
    public abstract ValueTask<RemoveSubscriptionResponse> RemoveSubscriptionAsync(RemoveSubscriptionRequest request, CancellationToken cancellationToken = default);
    public abstract ValueTask<List<Subscription>> GetSubscriptionsAsync(GetSubscriptionsRequest request, CancellationToken cancellationToken = default);

    private Agent GetOrActivateAgent(AgentId agentId)
    {
        if (!_agents.TryGetValue((agentId.Type, agentId.Key), out var agent))
        {
            if (_agentTypes.TryGetValue(agentId.Type, out var agentType))
            {
                using (var scope = RuntimeServiceProvider.CreateScope())
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
    private async ValueTask PublishEventAsync(CloudEvent item, Agent sender, CancellationToken cancellationToken = default)
    {
        var activity = Agent.s_source.StartActivity($"PublishEventAsync '{item.Type}'", ActivityKind.Client, Activity.Current?.Context ?? default);
        activity?.SetTag("peer.service", $"{item.Type}/{item.Source}");

        IAgentRuntimeExtensions.Update(this, item, activity);
        await sender.InvokeWithActivityAsync<(IAgentRuntime Worker, CloudEvent Event)>(
            async (state, ct) =>
            {
                await DispatchEventsToAgentsAsync(state.Event, cancellationToken).ConfigureAwait(false);
            },
            (this, item),
            activity,
            item.Type, cancellationToken).ConfigureAwait(false);
    }

    /// <summary>
    /// DispatchEventsToAgentsAsync
    /// writes CloudEvent to Agents
    /// </summary>
    /// <param name="cloudEvent">The CloudEvent to dispatch.</param>
    /// <param name="cancellationToken">The cancellation token.</param>
    private async ValueTask DispatchEventsToAgentsAsync(CloudEvent cloudEvent, CancellationToken cancellationToken = default)
    {
        var taskList = new List<Task>(capacity: _agentTypes.Count);
        foreach (var (typeName, _) in _agentTypes)
        {
            if (typeName == nameof(Client)) { continue; }
            var task = Task.Run(async () =>
            {
                var agent = GetOrActivateAgent(new AgentId { Type = typeName, Key = cloudEvent.GetSubject() });
                agent.ReceiveMessage(new Message { CloudEvent = cloudEvent });
            }, cancellationToken);
            taskList.Add(task);
        }
        await Task.WhenAll(taskList).ConfigureAwait(false);
    }

    public ValueTask RuntimeSendRequestAsync(Agent agent, RpcRequest request, CancellationToken cancellationToken = default)
    {
        throw new NotImplementedException();
    }

    public ValueTask RuntimeSendResponseAsync(RpcResponse response, CancellationToken cancellationToken = default)
    {
        throw new NotImplementedException();
    }
}
