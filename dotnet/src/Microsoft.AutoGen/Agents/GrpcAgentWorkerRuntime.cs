using System.Collections.Concurrent;
using System.Diagnostics;
using System.Reflection;
using System.Threading.Channels;
using Grpc.Core;
using Microsoft.AutoGen.Abstractions;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;

namespace Microsoft.AutoGen.Agents;

public sealed class GrpcAgentWorkerRuntime : IHostedService, IDisposable, IAgentWorkerRuntime
{
    private readonly object _channelLock = new();
    private readonly ConcurrentDictionary<string, Type> _agentTypes = new();
    private readonly ConcurrentDictionary<(string Type, string Key), IAgentBase> _agents = new();
    private readonly ConcurrentDictionary<string, (IAgentBase Agent, string OriginalRequestId)> _pendingRequests = new();
    private readonly Channel<Message> _outboundMessagesChannel = Channel.CreateBounded<Message>(new BoundedChannelOptions(1024)
    {
        AllowSynchronousContinuations = true,
        SingleReader = true,
        SingleWriter = false,
        FullMode = BoundedChannelFullMode.Wait
    });
    private readonly AgentRpc.AgentRpcClient _client;
    private readonly IServiceProvider _serviceProvider;
    private readonly IEnumerable<Tuple<string, Type>> _configuredAgentTypes;
    private readonly ILogger<GrpcAgentWorkerRuntime> _logger;
    private readonly DistributedContextPropagator _distributedContextPropagator;
    private readonly CancellationTokenSource _shutdownCts;
    private AsyncDuplexStreamingCall<Message, Message>? _channel;
    private Task? _readTask;
    private Task? _writeTask;

    public GrpcAgentWorkerRuntime(
        AgentRpc.AgentRpcClient client,
        IHostApplicationLifetime hostApplicationLifetime,
        IServiceProvider serviceProvider,
        [FromKeyedServices("AgentTypes")] IEnumerable<Tuple<string, Type>> configuredAgentTypes,
        ILogger<GrpcAgentWorkerRuntime> logger,
        DistributedContextPropagator distributedContextPropagator)
    {
        _client = client;
        _serviceProvider = serviceProvider;
        _configuredAgentTypes = configuredAgentTypes;
        _logger = logger;
        _distributedContextPropagator = distributedContextPropagator;
        _shutdownCts = CancellationTokenSource.CreateLinkedTokenSource(hostApplicationLifetime.ApplicationStopping);
    }

    public void Dispose()
    {
        _outboundMessagesChannel.Writer.TryComplete();
        _channel?.Dispose();
    }

    private async Task RunReadPump()
    {
        var channel = GetChannel();
        while (!_shutdownCts.Token.IsCancellationRequested)
        {
            try
            {
                await foreach (var message in channel.ResponseStream.ReadAllAsync(_shutdownCts.Token))
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
                channel = RecreateChannel(channel);
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
        var channel = GetChannel();
        var outboundMessages = _outboundMessagesChannel.Reader;
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
                    await channel.RequestStream.WriteAsync(message, _shutdownCts.Token).ConfigureAwait(false);
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
                channel = RecreateChannel(channel);
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

    private async ValueTask RegisterAgentType(string type, Type agentType)
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
            }).ConfigureAwait(false);
        }
    }

    public async ValueTask SendResponse(RpcResponse response)
    {
        _logger.LogInformation("Sending response '{Response}'.", response);
        await WriteChannelAsync(new Message { Response = response }).ConfigureAwait(false);
    }

    public async ValueTask SendRequest(IAgentBase agent, RpcRequest request)
    {
        _logger.LogInformation("[{AgentId}] Sending request '{Request}'.", agent.AgentId, request);
        var requestId = Guid.NewGuid().ToString();
        _pendingRequests[requestId] = (agent, request.RequestId);
        request.RequestId = requestId;
        await WriteChannelAsync(new Message { Request = request }).ConfigureAwait(false);
    }

    public async ValueTask PublishEvent(CloudEvent @event)
    {
        await WriteChannelAsync(new Message { CloudEvent = @event }).ConfigureAwait(false);
    }

    private async Task WriteChannelAsync(Message message)
    {
        await _outboundMessagesChannel.Writer.WriteAsync(message).ConfigureAwait(false);
    }

    private AsyncDuplexStreamingCall<Message, Message> GetChannel()
    {
        if (_channel is { } channel)
        {
            return channel;
        }

        lock (_channelLock)
        {
            if (_channel is not null)
            {
                return _channel;
            }

            return RecreateChannel(null);
        }
    }

    private AsyncDuplexStreamingCall<Message, Message> RecreateChannel(AsyncDuplexStreamingCall<Message, Message>? channel)
    {
        if (_channel is null || _channel == channel)
        {
            lock (_channelLock)
            {
                if (_channel is null || _channel == channel)
                {
                    _channel?.Dispose();
                    _channel = _client.OpenChannel();
                }
            }
        }

        return _channel;
    }

    public async Task StartAsync(CancellationToken cancellationToken)
    {
        _channel = GetChannel();
        StartCore();

        var tasks = new List<Task>(_agentTypes.Count);
        foreach (var (typeName, type) in _configuredAgentTypes)
        {
            tasks.Add(RegisterAgentType(typeName, type).AsTask());
        }

        await Task.WhenAll(tasks).ConfigureAwait(false);

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

        _outboundMessagesChannel.Writer.TryComplete();

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
            _channel?.Dispose();
        }
    }
    public ValueTask Store(AgentState value)
    {
        var agentId = value.AgentId ?? throw new InvalidOperationException("AgentId is required when saving AgentState.");
        var response = _client.SaveState(value);
        if (!response.Success)
        {
            throw new InvalidOperationException($"Error saving AgentState for AgentId {agentId}.");
        }
        return ValueTask.CompletedTask;
    }
    public async ValueTask<AgentState> Read(AgentId agentId)
    {
        var response = await _client.GetStateAsync(agentId);
        //        if (response.Success && response.AgentState.AgentId is not null) - why is success always false?
        if (response.AgentState.AgentId is not null)
        {
            return response.AgentState;
        }
        else
        {
            throw new KeyNotFoundException($"Failed to read AgentState for {agentId}.");
        }
    }
}

