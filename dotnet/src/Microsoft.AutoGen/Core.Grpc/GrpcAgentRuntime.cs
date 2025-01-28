// Copyright (c) Microsoft Corporation. All rights reserved.
// GrpcAgentRuntime.cs

using System.Collections.Concurrent;
using System.Threading.Channels;
using Google.Protobuf;
using Grpc.Core;
using Microsoft.AutoGen.Contracts;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;
using Microsoft.AutoGen.Protobuf;

namespace Microsoft.AutoGen.Core.Grpc;

public sealed class GrpcAgentRuntime(
    AgentRpc.AgentRpcClient client,
    IHostApplicationLifetime hostApplicationLifetime,
    IServiceProvider serviceProvider,
    ILogger<GrpcAgentRuntime> logger
    ) : IAgentRuntime, IDisposable
{
    private readonly object _channelLock = new();

    // Request ID ->
    private readonly ConcurrentDictionary<string, ResultSink<object?>> _pendingRequests = new();
    private Dictionary<AgentType, Func<Contracts.AgentId, IAgentRuntime, ValueTask<IHostableAgent>>> agentFactories = new();
    private Dictionary<Contracts.AgentId, IHostableAgent> agentInstances = new();

    private readonly Channel<(Message Message, TaskCompletionSource WriteCompletionSource)> _outboundMessagesChannel = Channel.CreateBounded<(Message, TaskCompletionSource)>(new BoundedChannelOptions(1024)
    {
        AllowSynchronousContinuations = true,
        SingleReader = true,
        SingleWriter = false,
        FullMode = BoundedChannelFullMode.Wait
    });

    private readonly AgentRpc.AgentRpcClient _client = client;
    public readonly IServiceProvider ServiceProvider = serviceProvider;

    private readonly ILogger<GrpcAgentRuntime> _logger = logger;
    private readonly CancellationTokenSource _shutdownCts = CancellationTokenSource.CreateLinkedTokenSource(hostApplicationLifetime.ApplicationStopping);
    private AsyncDuplexStreamingCall<Message, Message>? _channel;
    private Task? _readTask;
    private Task? _writeTask;

    private string _clientId = Guid.NewGuid().ToString();
    private CallOptions CallOptions
    {
        get
        {
            var metadata = new Metadata
            {
                { "client-id", this._clientId }
            };
            return new CallOptions(headers: metadata);
        }
    }

    public IProtoSerializationRegistry SerializationRegistry { get; } = new ProtoSerializationRegistry();

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
                            var request = message.Request ?? throw new InvalidOperationException("Request is null.");
                            await HandleRequest(request);
                            break;
                        case Message.MessageOneofCase.Response:
                            var response = message.Response ?? throw new InvalidOperationException("Response is null.");
                            await HandleResponse(response);
                            break;
                        case Message.MessageOneofCase.CloudEvent:
                            var cloudEvent = message.CloudEvent ?? throw new InvalidOperationException("CloudEvent is null.");
                            await HandlePublish(cloudEvent);
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

    private async ValueTask HandleRequest(RpcRequest request, CancellationToken cancellationToken = default)
    {
        if (request is null)
        {
            throw new InvalidOperationException("Request is null.");
        }
        if (request.Payload is null)
        {
            throw new InvalidOperationException("Payload is null.");
        }
        if (request.Target is null)
        {
            throw new InvalidOperationException("Target is null.");
        }
        if (request.Source is null)
        {
            throw new InvalidOperationException("Source is null.");
        }

        var agentId = request.Target;
        var agent = await EnsureAgentAsync(agentId.FromProtobuf());

        // Convert payload back to object
        var payload = request.Payload;
        var message = PayloadToObject(payload);

        var messageContext = new MessageContext(request.RequestId, cancellationToken)
        {
            Sender = request.Source.FromProtobuf(),
            Topic = null,
            IsRpc = true
        };

        var result = await agent.OnMessageAsync(message, messageContext);

        if (result is not null)
        {
            var response = new RpcResponse
            {
                RequestId = request.RequestId,
                Payload = ObjectToPayload(result)
            };

            var responseMessage = new Message
            {
                Response = response
            };

            await WriteChannelAsync(responseMessage, cancellationToken);
        }
    }

    private async ValueTask HandleResponse(RpcResponse request, CancellationToken _ = default)
    {
        if (request is null)
        {
            throw new InvalidOperationException("Request is null.");
        }
        if (request.Payload is null)
        {
            throw new InvalidOperationException("Payload is null.");
        }
        if (request.RequestId is null)
        {
            throw new InvalidOperationException("RequestId is null.");
        }

        if (_pendingRequests.TryRemove(request.RequestId, out var resultSink))
        {
            var payload = request.Payload;
            var message = PayloadToObject(payload);
            resultSink.SetResult(message);
        }
    }

    private async ValueTask HandlePublish(CloudEvent evt, CancellationToken cancellationToken = default)
    {
        if (evt is null)
        {
            throw new InvalidOperationException("CloudEvent is null.");
        }
        if (evt.ProtoData is null)
        {
            throw new InvalidOperationException("ProtoData is null.");
        }
        if (evt.Attributes is null)
        {
            throw new InvalidOperationException("Attributes is null.");
        }

        var topic = new TopicId(evt.Type, evt.Source);
        var sender = new Contracts.AgentId
        {
            Type = evt.Attributes["agagentsendertype"].CeString,
            Key = evt.Attributes["agagentsenderkey"].CeString
        };

        var messageId = evt.Id;
        var typeName = evt.Attributes["dataschema"].CeString;
        var serializer = SerializationRegistry.GetSerializer(typeName) ?? throw new Exception();
        var message = serializer.Deserialize(evt.ProtoData);

        var messageContext = new MessageContext(messageId, cancellationToken)
        {
            Sender = sender,
            Topic = topic,
            IsRpc = false
        };
        var agent = await EnsureAgentAsync(sender);
        await agent.OnMessageAsync(message, messageContext);
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

    // private override async ValueTask<RpcResponse> SendMessageAsync(Payload message, AgentId agentId, AgentId? agent = null, CancellationToken? cancellationToken = default)
    // {
    //     var request = new RpcRequest
    //     {
    //         RequestId = Guid.NewGuid().ToString(),
    //         Source = agent,
    //         Target = agentId,
    //         Payload = message,
    //     };

    //     // Actually send it and wait for the response
    //     throw new NotImplementedException();
    // }

    // new is intentional

    // public new async ValueTask RuntimeSendRequestAsync(IAgent agent, RpcRequest request, CancellationToken cancellationToken = default)
    // {
    //     var requestId = Guid.NewGuid().ToString();
    //     _pendingRequests[requestId] = ((Agent)agent, request.RequestId);
    //     request.RequestId = requestId;
    //     await WriteChannelAsync(new Message { Request = request }, cancellationToken).ConfigureAwait(false);
    // }

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
    public async Task StartAsync(CancellationToken cancellationToken)
    {
        _channel = GetChannel();
        _logger.LogInformation("Starting " + GetType().Name + ",connecting to gRPC endpoint " + Environment.GetEnvironmentVariable("AGENT_HOST"));
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

    private async ValueTask<IHostableAgent> EnsureAgentAsync(Contracts.AgentId agentId)
    {
        if (!this.agentInstances.TryGetValue(agentId, out IHostableAgent? agent))
        {
            if (!this.agentFactories.TryGetValue(agentId.Type, out Func<Contracts.AgentId, IAgentRuntime, ValueTask<IHostableAgent>>? factoryFunc))
            {
                throw new Exception($"Agent with name {agentId.Type} not found.");
            }

            agent = await factoryFunc(agentId, this);
            this.agentInstances.Add(agentId, agent);
        }

        return this.agentInstances[agentId];
    }

    private Payload ObjectToPayload(object message) {
        if (!SerializationRegistry.Exists(message.GetType()))
        {
            SerializationRegistry.RegisterSerializer(message.GetType());
        }
        var rpcMessage = (SerializationRegistry.GetSerializer(message.GetType()) ?? throw new Exception()).Serialize(message);

        var typeName = SerializationRegistry.TypeNameResolver.ResolveTypeName(message);
        const string PAYLOAD_DATA_CONTENT_TYPE = "application/x-protobuf";

        // Protobuf any to byte array
        Payload payload = new()
        {
            DataType = typeName,
            DataContentType = PAYLOAD_DATA_CONTENT_TYPE,
            Data = rpcMessage.ToByteString()
        };

        return payload;
    }

    private object PayloadToObject(Payload payload) {
        var typeName = payload.DataType;
        var data = payload.Data;
        var type = SerializationRegistry.TypeNameResolver.ResolveTypeName(typeName);
        var serializer = SerializationRegistry.GetSerializer(type) ?? throw new Exception();
        var any = Google.Protobuf.WellKnownTypes.Any.Parser.ParseFrom(data);
        return serializer.Deserialize(any);
    }

    public async ValueTask<object?> SendMessageAsync(object message, Contracts.AgentId recepient, Contracts.AgentId? sender = null, string? messageId = null, CancellationToken cancellationToken = default)
    {
        if (!SerializationRegistry.Exists(message.GetType()))
        {
            SerializationRegistry.RegisterSerializer(message.GetType());
        }

        var payload = ObjectToPayload(message);
        var request = new RpcRequest
        {
            RequestId = Guid.NewGuid().ToString(),
            Source = (sender ?? new Contracts.AgentId() ).ToProtobuf(),
            Target = recepient.ToProtobuf(),
            Payload = payload,
        };

        Message msg = new()
        {
            Request = request
        };
        // Create a future that will be completed when the response is received
        var resultSink = new ResultSink<object?>();
        this._pendingRequests.TryAdd(request.RequestId, resultSink);
        await WriteChannelAsync(msg, cancellationToken);

        return await resultSink.Future;
    }

    private CloudEvent CreateCloudEvent(Google.Protobuf.WellKnownTypes.Any payload, TopicId topic, string dataType, Contracts.AgentId sender, string messageId)
    {
        const string PAYLOAD_DATA_CONTENT_TYPE = "application/x-protobuf";
        return new CloudEvent
        {
            ProtoData = payload,
            Type = topic.Type,
            Source = topic.Source,
            Id = messageId,
            Attributes = {
                {
                    "datacontenttype", new CloudEvent.Types.CloudEventAttributeValue { CeString = PAYLOAD_DATA_CONTENT_TYPE }
                },
                {
                    "dataschema", new CloudEvent.Types.CloudEventAttributeValue { CeString = dataType }
                },
                {
                    "agagentsendertype", new CloudEvent.Types.CloudEventAttributeValue { CeString = sender.Type }
                },
                {
                    "agagentsenderkey", new CloudEvent.Types.CloudEventAttributeValue { CeString = sender.Key }
                },
                {
                    "agmsgkind", new CloudEvent.Types.CloudEventAttributeValue { CeString = "publish" }
                }
            }
        };
    }

    public async ValueTask PublishMessageAsync(object message, TopicId topic, Contracts.AgentId? sender = null, string? messageId = null, CancellationToken cancellationToken = default)
    {
        if (!SerializationRegistry.Exists(message.GetType()))
        {
            SerializationRegistry.RegisterSerializer(message.GetType());
        }
        var protoAny = (SerializationRegistry.GetSerializer(message.GetType()) ?? throw new Exception()).Serialize(message);
        var typeName = SerializationRegistry.TypeNameResolver.ResolveTypeName(message);

        var cloudEvent = CreateCloudEvent(protoAny, topic, typeName, sender ?? new Contracts.AgentId(), messageId ?? Guid.NewGuid().ToString());

        Message msg = new()
        {
            CloudEvent = cloudEvent
        };
        await WriteChannelAsync(msg, cancellationToken);
    }

    public ValueTask<Contracts.AgentId> GetAgentAsync(Contracts.AgentId agentId, bool lazy = true)
    {
        throw new NotImplementedException();
    }

    public ValueTask<Contracts.AgentId> GetAgentAsync(AgentType agentType, string key = "default", bool lazy = true)
    {
        throw new NotImplementedException();
    }

    public ValueTask<Contracts.AgentId> GetAgentAsync(string agent, string key = "default", bool lazy = true)
    {
        throw new NotImplementedException();
    }

    public ValueTask<IDictionary<string, object>> SaveAgentStateAsync(Contracts.AgentId agentId)
    {
        throw new NotImplementedException();
    }

    public ValueTask LoadAgentStateAsync(Contracts.AgentId agentId, IDictionary<string, object> state)
    {
        throw new NotImplementedException();
    }

    public ValueTask<AgentMetadata> GetAgentMetadataAsync(Contracts.AgentId agentId)
    {
        throw new NotImplementedException();
    }

    public async ValueTask AddSubscriptionAsync(ISubscriptionDefinition subscription)
    {
        var _ = await this._client.AddSubscriptionAsync(new AddSubscriptionRequest{
            Subscription = subscription.ToProtobuf()
        },this.CallOptions);
    }

    public ValueTask RemoveSubscriptionAsync(string subscriptionId)
    {
        throw new NotImplementedException();
    }

    public ValueTask<AgentType> RegisterAgentFactoryAsync(AgentType type, Func<Contracts.AgentId, IAgentRuntime, ValueTask<IHostableAgent>> factoryFunc)
    {
        if (this.agentFactories.ContainsKey(type))
        {
            throw new Exception($"Agent with type {type} already exists.");
        }
        this.agentFactories.Add(type, async (agentId, runtime) => await factoryFunc(agentId, runtime));

        this._client.RegisterAgentAsync(new RegisterAgentTypeRequest
        {
            Type = type.Name,

        }, this.CallOptions);
        return ValueTask.FromResult(type);
    }

    public ValueTask<AgentProxy> TryGetAgentProxyAsync(Contracts.AgentId agentId)
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

