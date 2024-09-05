using Agents;
using Grpc.Core;
using Microsoft.Extensions.Hosting;
using System.Collections.Concurrent;
using RpcEvent = Agents.Event;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.DependencyInjection;
using System.Threading.Channels;
using Grpc.Net.Client.Configuration;
using System.Diagnostics;
using System.Diagnostics.CodeAnalysis;
using Microsoft.Extensions.DependencyInjection.Extensions;
using static System.Diagnostics.CodeAnalysis.DynamicallyAccessedMemberTypes;

namespace Microsoft.AI.Agents.Worker.Client;

public static class HostBuilderExtensions
{
    public static AgentApplicationBuilder AddAgentWorker(this IHostApplicationBuilder builder, string agentServiceAddress)
    {
        builder.Services.AddGrpcClient<AgentRpc.AgentRpcClient>(options =>
        {
            options.Address = new Uri(agentServiceAddress);
            options.ChannelOptionsActions.Add(channelOptions =>
            {

                channelOptions.HttpHandler = new SocketsHttpHandler
                {
                    EnableMultipleHttp2Connections = true,
                    KeepAlivePingDelay = TimeSpan.FromSeconds(20),
                    KeepAlivePingTimeout = TimeSpan.FromSeconds(10),
                    KeepAlivePingPolicy = HttpKeepAlivePingPolicy.WithActiveRequests
                };

                var methodConfig = new MethodConfig
                {
                    Names = { MethodName.Default },
                    RetryPolicy = new RetryPolicy
                    {
                        MaxAttempts = 5,
                        InitialBackoff = TimeSpan.FromSeconds(1),
                        MaxBackoff = TimeSpan.FromSeconds(5),
                        BackoffMultiplier = 1.5,
                        RetryableStatusCodes = { StatusCode.Unavailable }
                    }
                };

                channelOptions.ServiceConfig = new() { MethodConfigs = { methodConfig } };
                channelOptions.ThrowOperationCanceledOnCancellation = true;
            });
        });
        builder.Services.TryAddSingleton(DistributedContextPropagator.Current);
        builder.Services.AddSingleton<AgentWorkerRuntime>();
        builder.Services.AddSingleton<IHostedService>(sp => sp.GetRequiredService<AgentWorkerRuntime>());
        return new AgentApplicationBuilder(builder);
    }
}

public sealed class AgentApplicationBuilder(IHostApplicationBuilder builder)
{
    public AgentApplicationBuilder AddAgent<
        [DynamicallyAccessedMembers(PublicConstructors)] TAgent>(string typeName) where TAgent : AgentBase
    {
        builder.Services.AddKeyedSingleton("AgentTypes", (sp, key) => Tuple.Create(typeName, typeof(TAgent)));
        return this;
    }
}

public sealed class AgentWorkerRuntime : IHostedService, IDisposable
{
    private readonly object _channelLock = new();
    private readonly ConcurrentDictionary<string, Type> _agentTypes = new();
    private readonly ConcurrentDictionary<(string Type, string Key), AgentBase> _agents = new();
    private readonly ConcurrentDictionary<string, (AgentBase Agent, string OriginalRequestId)> _pendingRequests = new();
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
    private readonly ILogger<AgentWorkerRuntime> _logger;
    private readonly DistributedContextPropagator _distributedContextPropagator;
    private readonly CancellationTokenSource _shutdownCts;
    private AsyncDuplexStreamingCall<Message, Message>? _channel;
    private Task? _readTask;
    private Task? _writeTask;

    public AgentWorkerRuntime(
        AgentRpc.AgentRpcClient client,
        IHostApplicationLifetime hostApplicationLifetime,
        IServiceProvider serviceProvider,
        [FromKeyedServices("AgentTypes")] IEnumerable<Tuple<string, Type>> configuredAgentTypes,
        ILogger<AgentWorkerRuntime> logger,
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
                        case Message.MessageOneofCase.Event:

                            // HACK: Send the message to an instance of each agent type
                            // where AgentId = (namespace: event.Namespace, name: agentType)
                            // i.e, assume each agent type implicitly subscribes to each event.

                            var item = message.Event;
                            foreach (var (typeName, _) in _agentTypes)
                            {
                                var agent = GetOrActivateAgent(new AgentId(typeName, item.TopicSource));
                                agent.ReceiveMessage(message);
                            }

                            break;
                        default:
                            throw new InvalidOperationException($"Unexpected message '{message}'.");
                    }
                }
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error reading from channel.");
                channel = RecreateChannel(channel);
            }
        }
    }

    private async Task RunWritePump()
    {
        var channel = GetChannel();
        var outboundMessages = _outboundMessagesChannel.Reader;
        while (!_shutdownCts.IsCancellationRequested)
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
                try
                {
                    await channel.RequestStream.WriteAsync(message, _shutdownCts.Token).ConfigureAwait(false);
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
    }

    private AgentBase GetOrActivateAgent(AgentId agentId)
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
            await WriteChannelAsync(new Message
            {
                RegisterAgentType = new RegisterAgentType
                {
                    Type = type,
                }
            }).ConfigureAwait(false);
        }
    }

    public async ValueTask SendResponse(RpcResponse response)
    {
        _logger.LogInformation("Sending response '{Response}'.", response);
        await WriteChannelAsync(new Message { Response = response }).ConfigureAwait(false);
    }

    public async ValueTask SendRequest(AgentBase agent, RpcRequest request)
    {
        _logger.LogInformation("[{AgentId}] Sending request '{Request}'.", agent.AgentId, request);
        var requestId = Guid.NewGuid().ToString();
        _pendingRequests[requestId] = (agent, request.RequestId);
        request.RequestId = requestId;
        await WriteChannelAsync(new Message { Request = request }).ConfigureAwait(false);
    }

    public async ValueTask PublishEvent(RpcEvent @event)
    {
        await WriteChannelAsync(new Message { Event = @event }).ConfigureAwait(false);
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
        lock (_channelLock)
        {
            _channel?.Dispose();
        }

        _outboundMessagesChannel.Writer.TryComplete();

        if (_readTask is { } readTask)
        {
            await readTask.ConfigureAwait(false);
        }

        if (_writeTask is { } writeTask)
        {
            await writeTask.ConfigureAwait(false);
        }
    }
}

