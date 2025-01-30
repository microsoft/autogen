// Copyright (c) Microsoft Corporation. All rights reserved.
// GrpcAgentRuntime.cs

using System.Collections.Concurrent;
using Grpc.Core;
using Microsoft.AutoGen.Contracts;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;
using Microsoft.AutoGen.Protobuf;

namespace Microsoft.AutoGen.Core.Grpc;

internal sealed class AgentsContainer(IAgentRuntime hostingRuntime)
{
    private readonly IAgentRuntime hostingRuntime = hostingRuntime;

    private Dictionary<Contracts.AgentId, IHostableAgent> agentInstances = new();
    private Dictionary<string, ISubscriptionDefinition> subscriptions = new();
    private Dictionary<AgentType, Func<Contracts.AgentId, IAgentRuntime, ValueTask<IHostableAgent>>> agentFactories = new();

    public async ValueTask<IHostableAgent> EnsureAgentAsync(Contracts.AgentId agentId)
    {
        if (!this.agentInstances.TryGetValue(agentId, out IHostableAgent? agent))
        {
            if (!this.agentFactories.TryGetValue(agentId.Type, out Func<Contracts.AgentId, IAgentRuntime, ValueTask<IHostableAgent>>? factoryFunc))
            {
                throw new Exception($"Agent with name {agentId.Type} not found.");
            }

            agent = await factoryFunc(agentId, this.hostingRuntime);
            this.agentInstances.Add(agentId, agent);
        }

        return this.agentInstances[agentId];
    }

    public async ValueTask<Contracts.AgentId> GetAgentAsync(Contracts.AgentId agentId, bool lazy = true)
    {
        if (!lazy)
        {
            await this.EnsureAgentAsync(agentId);
        }

        return agentId;
    }

    public AgentType RegisterAgentFactory(AgentType type, Func<Contracts.AgentId, IAgentRuntime, ValueTask<IHostableAgent>> factoryFunc)
    {
        if (this.agentFactories.ContainsKey(type))
        {
            throw new Exception($"Agent factory with type {type} already exists.");
        }

        this.agentFactories.Add(type, factoryFunc);
        return type;
    }

    public void AddSubscription(ISubscriptionDefinition subscription)
    {
        if (this.subscriptions.ContainsKey(subscription.Id))
        {
            throw new Exception($"Subscription with id {subscription.Id} already exists.");
        }

        this.subscriptions.Add(subscription.Id, subscription);
    }

    public bool RemoveSubscriptionAsync(string subscriptionId)
    {
        if (!this.subscriptions.ContainsKey(subscriptionId))
        {
            throw new Exception($"Subscription with id {subscriptionId} does not exist.");
        }

        return this.subscriptions.Remove(subscriptionId);
    }

    public HashSet<AgentType> RegisteredAgentTypes => this.agentFactories.Keys.ToHashSet();
    public IEnumerable<IHostableAgent> LiveAgents => this.agentInstances.Values;
}

public sealed class GrpcAgentRuntime: IHostedService, IAgentRuntime, IMessageSink<Message>, IDisposable
{
    public GrpcAgentRuntime(AgentRpc.AgentRpcClient client,
                            IHostApplicationLifetime hostApplicationLifetime,
                            IServiceProvider serviceProvider,
                            ILogger<GrpcAgentRuntime> logger)
    {
        this._client = client;
        this._logger = logger;
        this._shutdownCts = CancellationTokenSource.CreateLinkedTokenSource(hostApplicationLifetime.ApplicationStopping);

        this._messageRouter = new GrpcMessageRouter(client, this, logger, this._shutdownCts.Token);
        this._agentsContainer = new AgentsContainer(this);

        this.ServiceProvider = serviceProvider;
    }

    // Request ID -> ResultSink<...>
    private readonly ConcurrentDictionary<string, ResultSink<object?>> _pendingRequests = new();

    private readonly AgentRpc.AgentRpcClient _client;
    private readonly GrpcMessageRouter _messageRouter;

    private readonly ILogger<GrpcAgentRuntime> _logger;
    private readonly CancellationTokenSource _shutdownCts;

    private readonly AgentsContainer _agentsContainer;
    
    public IServiceProvider ServiceProvider { get; }

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
        this._shutdownCts.Cancel();
        this._messageRouter.Dispose();
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
        var agent = await this._agentsContainer.EnsureAgentAsync(agentId.FromProtobuf());

        // Convert payload back to object
        var payload = request.Payload;
        var message = this.SerializationRegistry.PayloadToObject(payload);

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
                Payload = this.SerializationRegistry.ObjectToPayload(result)
            };

            var responseMessage = new Message
            {
                Response = response
            };

            await this._messageRouter.RouteMessageAsync(responseMessage, cancellationToken);
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
            var message = this.SerializationRegistry.PayloadToObject(payload);
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
        var agent = await this._agentsContainer.EnsureAgentAsync(sender);
        await agent.OnMessageAsync(message, messageContext);
    }
   
    public ValueTask StartAsync(CancellationToken cancellationToken)
    {
        return this._messageRouter.StartAsync(cancellationToken);
    }

    Task IHostedService.StartAsync(CancellationToken cancellationToken) => this._messageRouter.StartAsync(cancellationToken).AsTask();

    public Task StopAsync(CancellationToken cancellationToken)
    {
        return this._messageRouter.StopAsync();
    }

    //private Payload ObjectToPayload(object message) {
    //    if (!SerializationRegistry.Exists(message.GetType()))
    //    {
    //        SerializationRegistry.RegisterSerializer(message.GetType());
    //    }
    //    var rpcMessage = (SerializationRegistry.GetSerializer(message.GetType()) ?? throw new Exception()).Serialize(message);

    //    var typeName = SerializationRegistry.TypeNameResolver.ResolveTypeName(message);
    //    const string PAYLOAD_DATA_CONTENT_TYPE = "application/x-protobuf";

    //    // Protobuf any to byte array
    //    Payload payload = new()
    //    {
    //        DataType = typeName,
    //        DataContentType = PAYLOAD_DATA_CONTENT_TYPE,
    //        Data = rpcMessage.ToByteString()
    //    };

    //    return payload;
    //}

    //private object PayloadToObject(Payload payload) {
    //    var typeName = payload.DataType;
    //    var data = payload.Data;
    //    var type = SerializationRegistry.TypeNameResolver.ResolveTypeName(typeName);
    //    var serializer = SerializationRegistry.GetSerializer(type) ?? throw new Exception();
    //    var any = Google.Protobuf.WellKnownTypes.Any.Parser.ParseFrom(data);
    //    return serializer.Deserialize(any);
    //}

    public async ValueTask<object?> SendMessageAsync(object message, Contracts.AgentId recepient, Contracts.AgentId? sender = null, string? messageId = null, CancellationToken cancellationToken = default)
    {
        if (!SerializationRegistry.Exists(message.GetType()))
        {
            SerializationRegistry.RegisterSerializer(message.GetType());
        }

        var payload = this.SerializationRegistry.ObjectToPayload(message);
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
        await this._messageRouter.RouteMessageAsync(msg, cancellationToken);

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

        await this._messageRouter.RouteMessageAsync(msg, cancellationToken);
    }

    public ValueTask<Contracts.AgentId> GetAgentAsync(Contracts.AgentId agentId, bool lazy = true) => this._agentsContainer.GetAgentAsync(agentId, lazy);

    public async ValueTask<IDictionary<string, object>> SaveAgentStateAsync(Contracts.AgentId agentId)
    {
        IHostableAgent agent = await this._agentsContainer.EnsureAgentAsync(agentId);
        return await agent.SaveStateAsync();
    }

    public async ValueTask LoadAgentStateAsync(Contracts.AgentId agentId, IDictionary<string, object> state)
    {
        IHostableAgent agent = await this._agentsContainer.EnsureAgentAsync(agentId);
        await agent.LoadStateAsync(state);
    }

    public async ValueTask<AgentMetadata> GetAgentMetadataAsync(Contracts.AgentId agentId)
    {
        IHostableAgent agent = await this._agentsContainer.EnsureAgentAsync(agentId);
        return agent.Metadata;
    }

    public ValueTask AddSubscriptionAsync(ISubscriptionDefinition subscription)
    {
        this._agentsContainer.AddSubscription(subscription);

        // Because we have an extensible definition of ISubscriptionDefinition, we cannot project it to the Gateway.
        // What this means is that we will have a much chattier interface between the Gateway and the Runtime.
        // TODO: We will be able to make this better by treating unknown subscription types as an "everything"
        // subscription. This will allow us to have a single subscription for all unknown types.

        //await this._client.AddSubscriptionAsync(new AddSubscriptionRequest
        //{
        //    Subscription = new Subscription
        //    {
        //        Id = subscription.Id,
        //        TopicType = subscription.TopicType,
        //        AgentType = subscription.AgentType.Name
        //    }
        //}, this.CallOptions);

        return ValueTask.CompletedTask;
    }

    public ValueTask RemoveSubscriptionAsync(string subscriptionId)
    {
        this._agentsContainer.RemoveSubscriptionAsync(subscriptionId);

        // See above (AddSubscriptionAsync) for why this is commented out.

        //await this._client.RemoveSubscriptionAsync(new RemoveSubscriptionRequest
        //{
        //    Id = subscriptionId
        //}, this.CallOptions);

        return ValueTask.CompletedTask;
    }

    public ValueTask<AgentType> RegisterAgentFactoryAsync(AgentType type, Func<Contracts.AgentId, IAgentRuntime, ValueTask<IHostableAgent>> factoryFunc)
        => ValueTask.FromResult(this._agentsContainer.RegisterAgentFactory(type, factoryFunc));

    public ValueTask<AgentProxy> TryGetAgentProxyAsync(Contracts.AgentId agentId)
    {
        // TODO: Do we want to support getting remote agent proxies?
        return ValueTask.FromResult(new AgentProxy(agentId, this));
    }

    public async ValueTask<IDictionary<string, object>> SaveStateAsync()
    {
        Dictionary<string, object> state = new();
        foreach (var agent in this._agentsContainer.LiveAgents)
        {
            state[agent.Id.ToString()] = await agent.SaveStateAsync();
        }

        return state;
    }

    public async ValueTask LoadStateAsync(IDictionary<string, object> state)
    {
        HashSet<AgentType> registeredTypes = this._agentsContainer.RegisteredAgentTypes;

        foreach (var agentIdStr in state.Keys)
        {
            Contracts.AgentId agentId = Contracts.AgentId.FromStr(agentIdStr);
            if (state[agentIdStr] is not IDictionary<string, object> agentStateDict)
            {
                throw new Exception($"Agent state for {agentId} is not a {typeof(IDictionary<string, object>)}: {state[agentIdStr].GetType()}");
            }

            if (registeredTypes.Contains(agentId.Type))
            {
                IHostableAgent agent = await this._agentsContainer.EnsureAgentAsync(agentId);
                await agent.LoadStateAsync(agentStateDict);
            }
        }
    }

    public async ValueTask OnMessageAsync(Message message, CancellationToken cancellation = default)
    {
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

