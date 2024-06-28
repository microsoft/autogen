using Agents;
using Grpc.Core;
using Microsoft.Extensions.Hosting;
using System.Collections.Concurrent;
using RpcEvent = Agents.Event;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.DependencyInjection;

namespace Microsoft.AI.Agents.Worker.Client;

public static class HostBuilderExtensions
{
    public static AgentApplicationBuilder AddAgentWorker(this IHostApplicationBuilder builder, string agentServiceAddress)
    {
        builder.Services.AddGrpcClient<AgentRpc.AgentRpcClient>(options => options.Address = new Uri(agentServiceAddress));
        builder.Services.AddSingleton<AgentWorkerRuntime>();
        builder.Services.AddSingleton<IHostedService>(sp => sp.GetRequiredService<AgentWorkerRuntime>());
        return new AgentApplicationBuilder(builder);
    }
}

public sealed class AgentApplicationBuilder(IHostApplicationBuilder builder)
{
    public AgentApplicationBuilder AddAgent<TAgent>(string typeName) where TAgent : AgentBase
    {
        builder.Services.AddKeyedSingleton("AgentTypes", (sp, key) => Tuple.Create(typeName, typeof(TAgent)));
        return this;
    }
}

public sealed class AgentWorkerRuntime(
    AgentRpc.AgentRpcClient client,
    IHostApplicationLifetime hostApplicationLifetime,
    IServiceProvider serviceProvider,
    [FromKeyedServices("AgentTypes")] IEnumerable<Tuple<string, Type>> agentTypes,
    ILogger<AgentWorkerRuntime> logger) : IHostedService, IDisposable
{
    private readonly object _channelLock = new();
    private readonly ConcurrentDictionary<string, Type> _agentTypes = new();
    private readonly ConcurrentDictionary<(string Type, string Key), AgentBase> _agents = new();
    private readonly ConcurrentDictionary<string, (AgentBase Agent, string OriginalRequestId)> _pendingRequests = new();

    private AsyncDuplexStreamingCall<Message, Message>? _channel;

    private Task? _runTask;

    public void Dispose()
    {
        _channel?.Dispose();
    }

    private async Task RunMessagePump()
    {
        while (!hostApplicationLifetime.ApplicationStopping.IsCancellationRequested)
        {
            var channel = GetChannel();
            try
            {
                await foreach (var message in channel.ResponseStream.ReadAllAsync(hostApplicationLifetime.ApplicationStopping))
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
                            foreach (var agent in _agents.Values)
                            {
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
                logger.LogError(ex, "Error reading from channel.");
                RecreateChannel(channel);
            }
        }
    }

    private AgentBase GetOrActivateAgent(AgentId agentId)
    {
        if (!_agents.TryGetValue((agentId.Name, agentId.Namespace), out var agent))
        {
            if (_agentTypes.TryGetValue(agentId.Name, out var agentType))
            {
                var context = new AgentContext(agentId, this, serviceProvider.GetRequiredService<ILogger<AgentBase>>());
                agent = (AgentBase)ActivatorUtilities.CreateInstance(serviceProvider, agentType, context);
                _agents.TryAdd((agentId.Name, agentId.Namespace), agent);
            }
            else
            {
                throw new InvalidOperationException($"Agent type '{agentId.Name}' is unknown.");
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
            });
        }
    }

    public async ValueTask SendResponse(RpcResponse response)
    {
        await WriteChannelAsync(new Message { Response = response });
    }

    public async ValueTask SendRequest(AgentBase agent, RpcRequest request)
    {
        var requestId = Guid.NewGuid().ToString();
        _pendingRequests[requestId] = (agent, request.RequestId);
        request.RequestId = requestId;
        await WriteChannelAsync(new Message { Request = request });
    }

    public async ValueTask PublishEvent(RpcEvent @event)
    {
        await WriteChannelAsync(new Message { Event = @event });
    }

    private async Task WriteChannelAsync(Message message)
    {
        var channel = GetChannel();
        try
        {
            await channel.RequestStream.WriteAsync(message);
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "Exception writing to channel.");
            RecreateChannel(channel);
        }
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
                    _channel = client.OpenChannel();
                }
            }
        }

        return _channel;
    }

    public async Task StartAsync(CancellationToken cancellationToken)
    {
        _channel = GetChannel();
        _runTask = Start();

        var tasks = new List<Task>(_agentTypes.Count);
        foreach (var (typeName, type) in agentTypes)
        {
            tasks.Add(RegisterAgentType(typeName, type).AsTask());
        }

        await Task.WhenAll(tasks);
    }

    internal Task Start()
    {
        var didSuppress = false;
        if (!ExecutionContext.IsFlowSuppressed())
        {
            didSuppress = true;
            ExecutionContext.SuppressFlow();
        }

        try
        {
            return Task.Run(RunMessagePump);
        }
        finally
        {
            if (didSuppress)
            {
                ExecutionContext.RestoreFlow();
            }
        }
    }

    public async Task StopAsync(CancellationToken cancellationToken)
    {
        lock (_channelLock)
        {
            _channel?.Dispose();
        }

        if (_runTask is { } task)
        {
            await task;
        }
    }
}

