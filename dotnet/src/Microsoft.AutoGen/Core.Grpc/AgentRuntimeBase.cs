// Copyright (c) Microsoft Corporation. All rights reserved.
// AgentRuntimeBase.cs

using System.Collections.Concurrent;
using Google.Protobuf;
using Microsoft.AutoGen.Contracts;
using Microsoft.AutoGen.Protobuf;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;
using AgentId = Microsoft.AutoGen.Contracts.AgentId;

namespace Microsoft.AutoGen.Core.Grpc;
/// <summary>
/// Base class for agent runtime.
/// </summary>
/// <param name="serviceProvider">the service host for DI container</param>
public abstract class AgentRuntimeBase(
    IServiceProvider serviceProvider,
    ILogger<AgentRuntimeBase> logger) : IAgentRuntime
{
    public IServiceProvider RuntimeServiceProvider { get; } = serviceProvider;
    private readonly ConcurrentDictionary<(string Type, string Key), BaseAgent> _agents = new();
    private readonly ConcurrentDictionary<string, Type> _agentTypes = new();
    protected readonly ILogger<AgentRuntimeBase> _logger = logger;
    protected BaseAgent GetOrActivateAgent(AgentId agentId)
    {
        if (!_agents.TryGetValue((agentId.Type, agentId.Key), out var agent))
        {
            if (_agentTypes.TryGetValue(agentId.Type, out var agentType))
            {
                using (var scope = RuntimeServiceProvider.CreateScope())
                {
                    var scopedProvider = scope.ServiceProvider;
                    agent = (BaseAgent)ActivatorUtilities.CreateInstance(scopedProvider, agentType);
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
    private async ValueTask PublishEventAsync(CloudEvent item, CancellationToken cancellationToken = default)
    {
        await DispatchEventsToAgentsAsync(item, cancellationToken).ConfigureAwait(false);
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
    public abstract ValueTask RuntimeSendRequestAsync(IAgent agent, RpcRequest request, CancellationToken cancellationToken = default);

    public abstract ValueTask RuntimeSendResponseAsync(RpcResponse response, CancellationToken cancellationToken = default);
    public abstract ValueTask<RpcResponse> SendMessageAsync(IMessage message, AgentId recipient, AgentId? sender, CancellationToken? cancellationToken = default);

    public ValueTask<object?> SendMessageAsync(object message, AgentId recepient, AgentId? sender = null, string? messageId = null, CancellationToken? cancellationToken = null)
    {
        throw new NotImplementedException();
    }

    public ValueTask PublishMessageAsync(object message, TopicId topic, AgentId? sender = null, string? messageId = null, CancellationToken? cancellationToken = null)
    {
        throw new NotImplementedException();
    }

    public ValueTask<AgentId> GetAgentAsync(AgentId agentId, bool lazy = true)
    {
        throw new NotImplementedException();
    }

    public ValueTask<AgentId> GetAgentAsync(AgentType agentType, string key = "default", bool lazy = true)
    {
        throw new NotImplementedException();
    }

    public ValueTask<AgentId> GetAgentAsync(string agent, string key = "default", bool lazy = true)
    {
        throw new NotImplementedException();
    }

    public ValueTask<IDictionary<string, object>> SaveAgentStateAsync(AgentId agentId)
    {
        throw new NotImplementedException();
    }

    public ValueTask LoadAgentStateAsync(AgentId agentId, IDictionary<string, object> state)
    {
        throw new NotImplementedException();
    }

    public ValueTask<AgentMetadata> GetAgentMetadataAsync(AgentId agentId)
    {
        throw new NotImplementedException();
    }

    public ValueTask AddSubscriptionAsync(ISubscriptionDefinition subscription)
    {
        throw new NotImplementedException();
    }

    public ValueTask RemoveSubscriptionAsync(string subscriptionId)
    {
        throw new NotImplementedException();
    }

    public ValueTask<AgentType> RegisterAgentFactoryAsync(AgentType type, Func<AgentId, IAgentRuntime, ValueTask<IHostableAgent>> factoryFunc)
    {
        throw new NotImplementedException();
    }

    public ValueTask<AgentProxy> TryGetAgentProxyAsync(AgentId agentId)
    {
        throw new NotImplementedException();
    }

    public ValueTask<IDictionary<string, object>> SaveStateAsync()
    {
        throw new NotImplementedException();
    }

    public ValueTask LoadStateAsync(IDictionary<string, object> state)
    {
        throw new NotImplementedException();
    }
}
