// Copyright (c) Microsoft Corporation. All rights reserved.
// AgentWorker.cs

using System.Collections.Concurrent;
using System.Diagnostics;
using System.Reflection;
using Microsoft.AutoGen.Abstractions;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;

namespace Microsoft.AutoGen.Agents;

public class AgentWorker(
    IHostApplicationLifetime hostApplicationLifetime,
    IServiceProvider serviceProvider,
    [FromKeyedServices("AgentTypes")] IEnumerable<Tuple<string, Type>> configuredAgentTypes,
    ILogger<GrpcAgentWorker> logger,
    DistributedContextPropagator distributedContextPropagator) :
     IHostedService,
     IAgentWorker
{
    private readonly ConcurrentDictionary<string, Type> _agentTypes = new();
    private readonly ConcurrentDictionary<(string Type, string Key), IAgentBase> _agents = new();
    private readonly ConcurrentDictionary<string, (IAgentBase Agent, string OriginalRequestId)> _pendingRequests = new();
    private readonly ILogger<AgentWorker> _logger = logger;
    private readonly InMemoryQueue<CloudEvent> _eventsQueue = new();
    private readonly InMemoryQueue<Message> _messageQueue = new();
    private readonly ConcurrentDictionary<string, AgentState> _agentStates = new();
    private readonly ConcurrentDictionary<string, (IAgentBase Agent, string OriginalRequestId)> _pendingClientRequests = new();
    private readonly CancellationTokenSource _shutdownCts = CancellationTokenSource.CreateLinkedTokenSource(hostApplicationLifetime.ApplicationStopping);
    private readonly IServiceProvider _serviceProvider = serviceProvider;
    private readonly IEnumerable<Tuple<string, Type>> _configuredAgentTypes = configuredAgentTypes;
    private readonly DistributedContextPropagator _distributedContextPropagator = distributedContextPropagator;

    private Task? _readTask;
    private Task? _writeTask;
    private readonly object _channelLock = new();

    public async ValueTask PublishEventAsync(CloudEvent evt, CancellationToken cancellationToken = default)
    {
        await this.WriteAsync(evt,cancellationToken).ConfigureAwait(false);
    }
    public ValueTask SendRequestAsync(IAgentBase agent, RpcRequest request, CancellationToken cancellationToken = default)
    {
        _logger.LogInformation("[{AgentId}] Sending request '{Request}'.", agent.AgentId, request);
        var requestId = Guid.NewGuid().ToString();
        _pendingClientRequests[requestId] = (agent, request.RequestId);
        request.RequestId = requestId;
        return this.WriteAsync(new Message { Request = request }, cancellationToken);
    }
    public ValueTask SendResponseAsync(RpcResponse response, CancellationToken cancellationToken = default)
    {
        _logger.LogInformation("Sending response '{Response}'.", response);
        return this.WriteAsync(new Message { Response = response }, cancellationToken);
    }
    public ValueTask StoreAsync(AgentState value, CancellationToken cancellationToken = default)
    {
        var agentId = value.AgentId ?? throw new InvalidOperationException("AgentId is required when saving AgentState.");
        var response = _agentStates.TryAdd(agentId.ToString(), value);
        if (!response)
        {
            throw new InvalidOperationException($"Error saving AgentState for AgentId {agentId}.");
        }
        return ValueTask.CompletedTask;
    }
    public ValueTask<AgentState> ReadAsync(AgentId agentId, CancellationToken cancellationToken = default)
    {
        _agentStates.TryGetValue(agentId.ToString(), out var state);
        //TODO: BUG:if (response.Success && response.AgentState.AgentId is not null) - why is success always false?
        if (state is not null && state.AgentId is not null)
        {
            return new ValueTask<AgentState>(state);
        }
        else
        {
            throw new KeyNotFoundException($"Failed to read AgentState for {agentId}.");
        }
    }
    // In-Memory specific implementations
    private ValueTask WriteAsync(Message message, CancellationToken cancellationToken = default)
    {
        return _messageQueue.Writer.WriteAsync(message, cancellationToken);
    }
    private ValueTask WriteAsync(CloudEvent evt, CancellationToken cancellationToken = default)
    {
        return _eventsQueue.Writer.WriteAsync(evt, cancellationToken);
    }
    private async Task WriteChannelAsync(Message message, CancellationToken cancellationToken = default)
    {
        await _messageQueue.Writer.WriteAsync(message, cancellationToken).ConfigureAwait(false);
    }
    private async ValueTask RegisterAgentTypeAsync(string type, Type agentType, CancellationToken cancellationToken = default)
    {
        if (_agentTypes.TryAdd(type, agentType))
        {
            var events = agentType.GetInterfaces()
            .Where(i => i.IsGenericType && i.GetGenericTypeDefinition() == typeof(IHandle<>))
            .Select(i => i.GetGenericArguments().First().Name);
            //var state = agentType.BaseType?.GetGenericArguments().First();
            var topicTypes = agentType.GetCustomAttributes<TopicSubscriptionAttribute>().Select(t => t.Topic);

            await WriteChannelAsync(new Message
            {
                RegisterAgentTypeRequest = new RegisterAgentTypeRequest
                {
                    Type = type,
                    RequestId = Guid.NewGuid().ToString(),
                    //TopicTypes = { topicTypes },
                    //StateType = state?.Name,
                    //Events = { events }
                }
            }, cancellationToken).ConfigureAwait(false);
        }
    }

    public async Task StartAsync(CancellationToken cancellationToken)
    {
        StartCore();

        var tasks = new List<Task>(_agentTypes.Count);
        foreach (var (typeName, type) in _configuredAgentTypes)
        {
            tasks.Add(RegisterAgentTypeAsync(typeName, type, cancellationToken).AsTask());
        }

        await Task.WhenAll(tasks).ConfigureAwait(true);

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
                _readTask = Task.Run(RunReadPump, CancellationToken.None);
                _writeTask = Task.Run(RunWritePump, CancellationToken.None);
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

        _messageQueue.Writer.TryComplete();

        if (_readTask is { } readTask)
        {
            await readTask.ConfigureAwait(false);
        }

        if (_writeTask is { } writeTask)
        {
            await writeTask.ConfigureAwait(false);
        }
        lock (_channelLock)
        {
        }
    }
    private async Task RunReadPump()
    {
        //var channel = GetChannel();
        while (!_shutdownCts.Token.IsCancellationRequested)
        {
            try
            {
                await foreach (var message in _messageQueue.Reader.ReadAllAsync(_shutdownCts.Token))
                {
                    // next if message is null
                    if (message == null)
                    {
                        continue;
                    }
                    switch (message.MessageCase)
                    {
                        case Message.MessageOneofCase.Request:
                            GetOrActivateAgent(message.Request.Target).ReceiveMessage(message);
                            break;
                        case Message.MessageOneofCase.Response:
                            if (!_pendingRequests.TryRemove(message.Response.RequestId, out var request))
                            {
                                throw new InvalidOperationException($"Unexpected response '{message.Response}'");
                            }

                            message.Response.RequestId = request.OriginalRequestId;
                            request.Agent.ReceiveMessage(message);
                            break;

                        case Message.MessageOneofCase.RegisterAgentTypeResponse:
                            if (!message.RegisterAgentTypeResponse.Success)
                            {
                                throw new InvalidOperationException($"Failed to register agent: '{message.RegisterAgentTypeResponse.Error}'.");
                            }
                            break;

                        case Message.MessageOneofCase.CloudEvent:

                            // HACK: Send the message to an instance of each agent type
                            // where AgentId = (namespace: event.Namespace, name: agentType)
                            // i.e, assume each agent type implicitly subscribes to each event.

                            var item = message.CloudEvent;

                            foreach (var (typeName, _) in _agentTypes)
                            {
                                var agent = GetOrActivateAgent(new AgentId(typeName, item.Source));
                                agent.ReceiveMessage(message);
                            }

                            break;
                        default:
                            throw new InvalidOperationException($"Unexpected message '{message}'.");
                    }
                }
            }
            catch (OperationCanceledException)
            {
                // Time to shut down.
                break;
            }
            catch (Exception ex) when (!_shutdownCts.IsCancellationRequested)
            {
                _logger.LogError(ex, "Error reading from channel.");
            }
            catch
            {
                // Shutdown requested.
                break;
            }
        }
    }
    private async Task RunWritePump()
    {
        var outboundMessages = _messageQueue.Reader;
        while (!_shutdownCts.IsCancellationRequested)
        {
            try
            {
                await outboundMessages.WaitToReadAsync().ConfigureAwait(false);

                // Read the next message if we don't already have an unsent message
                // waiting to be sent.
                if (!outboundMessages.TryRead(out var message))
                {
                    break;
                }

                while (!_shutdownCts.IsCancellationRequested)
                {
                    await _messageQueue.Writer.WriteAsync(message, _shutdownCts.Token).ConfigureAwait(false);
                    break;
                }
            }
            catch (OperationCanceledException)
            {
                // Time to shut down.
                break;
            }
            catch (Exception ex) when (!_shutdownCts.IsCancellationRequested)
            {
                _logger.LogError(ex, "Error writing to channel.");
                continue;
            }
            catch
            {
                // Shutdown requested.
                break;
            }
        }
    }
        private IAgentBase GetOrActivateAgent(AgentId agentId)
    {
        if (!_agents.TryGetValue((agentId.Type, agentId.Key), out var agent))
        {
            if (_agentTypes.TryGetValue(agentId.Type, out var agentType))
            {
                var context = new AgentContext(agentId, this, _serviceProvider.GetRequiredService<ILogger<AgentBase>>(), _distributedContextPropagator);
                agent = (AgentBase)ActivatorUtilities.CreateInstance(_serviceProvider, agentType, context);
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
