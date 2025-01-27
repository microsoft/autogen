// Copyright (c) Microsoft Corporation. All rights reserved.
// GrpcAgentRuntime.cs

using System.Collections.Concurrent;
using System.Reflection;
using System.Threading.Channels;
using Google.Protobuf;
using Grpc.Core;
using Microsoft.AutoGen.Contracts;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;

namespace Microsoft.AutoGen.Core.Grpc;

public sealed class GrpcAgentRuntime(
    AgentRpc.AgentRpcClient client,
    IHostApplicationLifetime hostApplicationLifetime,
    IServiceProvider serviceProvider,
    [FromKeyedServices("AgentTypes")] IEnumerable<Tuple<string, System.Type>> configuredAgentTypes,
    ILogger<GrpcAgentRuntime> logger
    ) : AgentRuntime(
        hostApplicationLifetime,
        serviceProvider,
        configuredAgentTypes,
        logger
        ), IDisposable
{
    private readonly object _channelLock = new();
    private readonly ConcurrentDictionary<string, global::System.Type> _agentTypes = new();
    private readonly ConcurrentDictionary<(string Type, string Key), Agent> _agents = new();
    private readonly ConcurrentDictionary<string, (Agent Agent, string OriginalRequestId)> _pendingRequests = new();
    private readonly ConcurrentDictionary<string, HashSet<global::System.Type>> _agentsForEvent = new();
    private readonly Channel<(Message Message, TaskCompletionSource WriteCompletionSource)> _outboundMessagesChannel = Channel.CreateBounded<(Message, TaskCompletionSource)>(new BoundedChannelOptions(1024)
    {
        AllowSynchronousContinuations = true,
        SingleReader = true,
        SingleWriter = false,
        FullMode = BoundedChannelFullMode.Wait
    });
    private readonly AgentRpc.AgentRpcClient _client = client;
    public readonly IServiceProvider ServiceProvider = serviceProvider;
    private readonly IEnumerable<Tuple<string, System.Type>> _configuredAgentTypes = configuredAgentTypes;
    private new readonly ILogger<GrpcAgentRuntime> _logger = logger;
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
                                _logger.LogError($"Failed to register agent type '{message.RegisterAgentTypeResponse.Error}'");
                            }
                            break;
                        case Message.MessageOneofCase.AddSubscriptionResponse:
                            if (!message.AddSubscriptionResponse.Success)
                            {
                                _logger.LogError($"Failed to add subscription '{message.AddSubscriptionResponse.Error}'");
                            }
                            break;
                        case Message.MessageOneofCase.CloudEvent:
                            var item = message.CloudEvent;
                            if (!_agentsForEvent.TryGetValue(item.Type, out var agents))
                            {
                                _logger.LogError($"This worker can't handle the event type '{item.Type}'.");
                                break;
                            }
                            foreach (var a in agents)
                            {
                                var subject = item.GetSubject();
                                if (string.IsNullOrEmpty(subject))
                                {
                                    subject = item.Source;
                                }
                                var agent = GetOrActivateAgent(new AgentId { Type = a.Name, Key = subject });
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
                _logger.LogError(ex, "Error connecting to GRPC endpoint {Endpoint}.", Environment.GetEnvironmentVariable("AGENT_HOST"));
                break;
            }
            catch (RpcException ex) when (ex.StatusCode == StatusCode.OK)
            {
                _logger.LogError(ex, "Error writing to channel, continuing (Status OK). {ex}", channel.ToString());
                break;
            }
            catch (Exception ex) when (!_shutdownCts.IsCancellationRequested)
            {
                item.WriteCompletionSource?.TrySetException(ex);
                _logger.LogError(ex, $"Error writing to channel.{ex}");
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
    private new Agent GetOrActivateAgent(AgentId agentId)
    {
        if (!_agents.TryGetValue((agentId.Type, agentId.Key), out var agent))
        {
            if (_agentTypes.TryGetValue(agentId.Type, out var agentType))
            {
                agent = (Agent)ActivatorUtilities.CreateInstance(ServiceProvider, agentType);
                Agent.Initialize(this, agent);
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
            .Select(i => ReflectionHelper.GetMessageDescriptor(i.GetGenericArguments().First())?.FullName);
            // add the agentType to the list of agent types that handle the event
            foreach (var evt in events)
            {
                if (!_agentsForEvent.TryGetValue(evt!, out var agents))
                {
                    agents = new HashSet<Type>();
                    _agentsForEvent[evt!] = agents;
                }

                agents.Add(agentType);
            }
            var topicTypes = agentType.GetCustomAttributes<TopicSubscriptionAttribute>().Select(t => t.Topic).ToList();
            /*             var response = await _client.RegisterAgentAsync(new RegisterAgentTypeRequest
                        {
                            Type = type,
                            Topics = { topicTypes },
                            Events = { events }
                        }, null, null, cancellationToken); */
            await WriteChannelAsync(new Message
            {
                RegisterAgentTypeRequest = new RegisterAgentTypeRequest
                {
                    RequestId = Guid.NewGuid().ToString(),
                    Type = type,
                    //Topics = { topicTypes }, //future
                    //Events = { events }   //future
                }
            }, cancellationToken).ConfigureAwait(false);
            if (!topicTypes.Any())
            {
                topicTypes.Add(agentType.Name);
            }
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
                await _client.AddSubscriptionAsync(subscriptionRequest.AddSubscriptionRequest, null, null, cancellationToken);
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
                    await _client.AddSubscriptionAsync(subscriptionRequest.AddSubscriptionRequest, null, null, cancellationToken);
                }
            }
        }
    }
    public override async ValueTask<RpcResponse> SendMessageAsync(IMessage message, AgentId agentId, AgentId? agent = null, CancellationToken? cancellationToken = default)
    {
        var request = new RpcRequest
        {
            RequestId = Guid.NewGuid().ToString(),
            Source = agent,
            Target = agentId,
            Payload = (Payload)message,
        };
        var response = await InvokeRequestAsync(request).ConfigureAwait(false);
        return response;
    }
    // new is intentional
    public new async ValueTask RuntimeSendResponseAsync(RpcResponse response, CancellationToken cancellationToken = default)
    {
        await WriteChannelAsync(new Message { Response = response }, cancellationToken).ConfigureAwait(false);
    }
    public new async ValueTask RuntimeSendRequestAsync(IAgent agent, RpcRequest request, CancellationToken cancellationToken = default)
    {
        var requestId = Guid.NewGuid().ToString();
        _pendingRequests[requestId] = ((Agent)agent, request.RequestId);
        request.RequestId = requestId;
        await WriteChannelAsync(new Message { Request = request }, cancellationToken).ConfigureAwait(false);
    }
    public new async ValueTask RuntimeWriteMessage(Message message, CancellationToken cancellationToken = default)
    {
        await WriteChannelAsync(message, cancellationToken).ConfigureAwait(false);
    }
    public async ValueTask RuntimePublishEventAsync(CloudEvent @event, CancellationToken cancellationToken = default)
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
        _logger.LogInformation("Starting " + GetType().Name + ",connecting to gRPC endpoint " + Environment.GetEnvironmentVariable("AGENT_HOST"));

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
                _readTask = Task.Run(RunReadPump, cancellationToken);
                _writeTask = Task.Run(RunWritePump, cancellationToken);
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
    public new async ValueTask SaveStateAsync(AgentState value, CancellationToken cancellationToken = default)
    {
        var agentId = value.AgentId ?? throw new InvalidOperationException("AgentId is required when saving AgentState.");
        var response = _client.SaveState(value, null, null, cancellationToken);
        if (!response.Success)
        {
            throw new InvalidOperationException($"Error saving AgentState for AgentId {agentId}.");
        }
    }

    public new async ValueTask<AgentState> LoadStateAsync(AgentId agentId, CancellationToken cancellationToken = default)
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
    public new async ValueTask<List<Subscription>> GetSubscriptionsAsync(GetSubscriptionsRequest request, CancellationToken cancellationToken = default)
    {
        var response = await _client.GetSubscriptionsAsync(request, null, null, cancellationToken);
        return response.Subscriptions.ToList();
    }
    public new async Task<AddSubscriptionResponse> AddSubscriptionAsync(AddSubscriptionRequest request, CancellationToken cancellationToken = default)
    {
        var response = _client.AddSubscription(request, null, null, cancellationToken);
        return response;
    }
    public new async ValueTask<RemoveSubscriptionResponse> RemoveSubscriptionAsync(RemoveSubscriptionRequest request, CancellationToken cancellationToken = default)
    {
        var response = _client.RemoveSubscription(request, null, null, cancellationToken);
        return response;
    }
}

