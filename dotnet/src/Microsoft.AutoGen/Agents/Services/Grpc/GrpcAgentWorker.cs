// Copyright (c) Microsoft Corporation. All rights reserved.
// GrpcAgentWorker.cs

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

public sealed class GrpcAgentWorker(
    AgentRpc.AgentRpcClient client,
    IHostApplicationLifetime hostApplicationLifetime,
    IServiceProvider serviceProvider,
    [FromKeyedServices("AgentTypes")] IEnumerable<Tuple<string, Type>> configuredAgentTypes,
    ILogger<GrpcAgentWorker> logger,
    DistributedContextPropagator distributedContextPropagator) :
    AgentWorker(hostApplicationLifetime,
    serviceProvider, configuredAgentTypes, logger, distributedContextPropagator), IHostedService, IDisposable, IAgentWorker
{
    private readonly object _channelLock = new();
    private readonly ConcurrentDictionary<string, Type> _agentTypes = new();
    private readonly ConcurrentDictionary<(string Type, string Key), IAgentBase> _agents = new();
    private readonly ConcurrentDictionary<string, (IAgentBase Agent, string OriginalRequestId)> _pendingRequests = new();
    private readonly Channel<(Message Message, TaskCompletionSource WriteCompletionSource)> _outboundMessagesChannel = Channel.CreateBounded<(Message, TaskCompletionSource)>(new BoundedChannelOptions(1024)
    {
        AllowSynchronousContinuations = true,
        SingleReader = true,
        SingleWriter = false,
        FullMode = BoundedChannelFullMode.Wait
    });
    private readonly AgentRpc.AgentRpcClient _client = client;
    private readonly IServiceProvider _serviceProvider = serviceProvider;
    private readonly IEnumerable<Tuple<string, Type>> _configuredAgentTypes = configuredAgentTypes;
    private readonly ILogger<GrpcAgentWorker> _logger = logger;
    private readonly DistributedContextPropagator _distributedContextPropagator = distributedContextPropagator;
    private readonly CancellationTokenSource _shutdownCts = CancellationTokenSource.CreateLinkedTokenSource(hostApplicationLifetime.ApplicationStopping);
    private AsyncDuplexStreamingCall<Message, Message>? _channel;
    private Task? _readTask;
    private Task? _writeTask;

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

                        case Message.MessageOneofCase.AddSubscriptionResponse:
                            if (!message.AddSubscriptionResponse.Success)
                            {
                                throw new InvalidOperationException($"Failed to add subscription: '{message.AddSubscriptionResponse.Error}'.");
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
            (Message Message, TaskCompletionSource WriteCompletionSource) item = default;
            try
            {
                await outboundMessages.WaitToReadAsync().ConfigureAwait(false);

                // Read the next message if we don't already have an unsent message
                // waiting to be sent.
                if (!outboundMessages.TryRead(out item))
                {
                    break;
                }

                while (!_shutdownCts.IsCancellationRequested)
                {
                    await channel.RequestStream.WriteAsync(item.Message, _shutdownCts.Token).ConfigureAwait(false);
                    item.WriteCompletionSource.TrySetResult();
                    break;
                }
            }
            catch (OperationCanceledException)
            {
                // Time to shut down.
                item.WriteCompletionSource?.TrySetCanceled();
                break;
            }
            catch (RpcException ex) when (ex.StatusCode == StatusCode.Unavailable)
            {
                // we could not connect to the endpoint - most likely we have the wrong port or failed ssl
                // we need to let the user know what port we tried to connect to and then do backoff and retry
                _logger.LogError(ex, "Error connecting to GRPC endpoint {Endpoint}.", channel.ToString());
                break;
            }
            catch (Exception ex) when (!_shutdownCts.IsCancellationRequested)
            {
                item.WriteCompletionSource?.TrySetException(ex);
                _logger.LogError(ex, "Error writing to channel.");
                channel = RecreateChannel(channel);
                continue;
            }
            catch
            {
                // Shutdown requested.
                item.WriteCompletionSource?.TrySetCanceled();
                break;
            }
        }

        while (outboundMessages.TryRead(out var item))
        {
            item.WriteCompletionSource.TrySetCanceled();
        }
    }
    private IAgentBase GetOrActivateAgent(AgentId agentId)
    {
        if (!_agents.TryGetValue((agentId.Type, agentId.Key), out var agent))
        {
            if (_agentTypes.TryGetValue(agentId.Type, out var agentType))
            {
                var context = new AgentRuntime(agentId, this, _serviceProvider.GetRequiredService<ILogger<AgentBase>>(), _distributedContextPropagator);
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

    private async ValueTask RegisterAgentTypeAsync(string type, Type agentType, CancellationToken cancellationToken = default)
    {
        if (_agentTypes.TryAdd(type, agentType))
        {
            var events = agentType.GetInterfaces()
            .Where(i => i.IsGenericType && i.GetGenericTypeDefinition() == typeof(IHandle<>))
            .Select(i => i.GetGenericArguments().First().Name);
            //var state = agentType.BaseType?.GetGenericArguments().First();
            var topicTypes = agentType.GetCustomAttributes<TopicSubscriptionAttribute>().Select(t => t.Topic);

            //TODO: do something with the response (like retry on error)
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

            foreach (var topic in topicTypes)
            {
                var subscriptionRequest = new Message
                {
                    AddSubscriptionRequest = new AddSubscriptionRequest
                    {
                        RequestId = Guid.NewGuid().ToString(),
                        Subscription = new Subscription
                        {
                            TypeSubscription = new TypeSubscription
                            {
                                AgentType = type,
                                TopicType = topic
                            }
                        }
                    }
                };
                await WriteChannelAsync(subscriptionRequest, cancellationToken).ConfigureAwait(true);
                foreach (var e in events)
                {
                    subscriptionRequest = new Message
                    {
                        AddSubscriptionRequest = new AddSubscriptionRequest
                        {
                            RequestId = Guid.NewGuid().ToString(),
                            Subscription = new Subscription
                            {
                                TypeSubscription = new TypeSubscription
                                {
                                    AgentType = type,
                                    TopicType = topic + "." + e
                                }
                            }
                        }
                    };
                    await WriteChannelAsync(subscriptionRequest, cancellationToken).ConfigureAwait(true);
                }
            }
        }
    }
    // new is intentional
    public new async ValueTask SendResponseAsync(RpcResponse response, CancellationToken cancellationToken = default)
    {
        await WriteChannelAsync(new Message { Response = response }, cancellationToken).ConfigureAwait(false);
    }
    // new is intentional
    public new async ValueTask SendRequestAsync(IAgentBase agent, RpcRequest request, CancellationToken cancellationToken = default)
    {
        var requestId = Guid.NewGuid().ToString();
        _pendingRequests[requestId] = (agent, request.RequestId);
        request.RequestId = requestId;
        await WriteChannelAsync(new Message { Request = request }, cancellationToken).ConfigureAwait(false);
    }
    // new is intentional
    public new async ValueTask SendMessageAsync(Message message, CancellationToken cancellationToken = default)
    {
        await WriteChannelAsync(message, cancellationToken).ConfigureAwait(false);
    }
    // new is intentional
    public new async ValueTask PublishEventAsync(CloudEvent @event, CancellationToken cancellationToken = default)
    {
        await WriteChannelAsync(new Message { CloudEvent = @event }, cancellationToken).ConfigureAwait(false);
    }
    private async Task WriteChannelAsync(Message message, CancellationToken cancellationToken = default)
    {
        var tcs = new TaskCompletionSource();
        await _outboundMessagesChannel.Writer.WriteAsync((message, tcs), cancellationToken).ConfigureAwait(false);
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
                    _channel = _client.OpenChannel(cancellationToken: _shutdownCts.Token);
                }
            }
        }

        return _channel;
    }

    public new async Task StartAsync(CancellationToken cancellationToken)
    {
        _channel = GetChannel();
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

    public new async Task StopAsync(CancellationToken cancellationToken)
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
    // new intentional
    public new async ValueTask StoreAsync(AgentState value, CancellationToken cancellationToken = default)
    {
        var agentId = value.AgentId ?? throw new InvalidOperationException("AgentId is required when saving AgentState.");
        var response = _client.SaveState(value, null, null, cancellationToken);
        if (!response.Success)
        {
            throw new InvalidOperationException($"Error saving AgentState for AgentId {agentId}.");
        }
    }
    // new intentional
    public new async ValueTask<AgentState> ReadAsync(AgentId agentId, CancellationToken cancellationToken = default)
    {
        var response = await _client.GetStateAsync(agentId).ConfigureAwait(true);
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

