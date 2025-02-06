// Copyright (c) Microsoft Corporation. All rights reserved.
// GrpcAgentRuntime.cs

using System.Collections.Concurrent;
using System.Text.Json;
using Grpc.Core;
using Microsoft.AutoGen.Contracts;
using Microsoft.AutoGen.Protobuf;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;

namespace Microsoft.AutoGen.Core.Grpc;

internal sealed class AgentsContainer(IAgentRuntime hostingRuntime)
{
    private readonly IAgentRuntime hostingRuntime = hostingRuntime;

    private Dictionary<Contracts.AgentId, IHostableAgent> agentInstances = new();
    public Dictionary<string, ISubscriptionDefinition> Subscriptions = new();
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
        if (this.Subscriptions.ContainsKey(subscription.Id))
        {
            throw new Exception($"Subscription with id {subscription.Id} already exists.");
        }

        this.Subscriptions.Add(subscription.Id, subscription);
    }

    public bool RemoveSubscriptionAsync(string subscriptionId)
    {
        if (!this.Subscriptions.ContainsKey(subscriptionId))
        {
            throw new Exception($"Subscription with id {subscriptionId} does not exist.");
        }

        return this.Subscriptions.Remove(subscriptionId);
    }

    public HashSet<AgentType> RegisteredAgentTypes => this.agentFactories.Keys.ToHashSet();
    public IEnumerable<IHostableAgent> LiveAgents => this.agentInstances.Values;
}

public sealed class GrpcAgentRuntime : IHostedService, IAgentRuntime, IMessageSink<Message>, IDisposable
{
    public GrpcAgentRuntime(AgentRpc.AgentRpcClient client,
                            IHostApplicationLifetime hostApplicationLifetime,
                            IServiceProvider serviceProvider,
                            ILogger<GrpcAgentRuntime> logger)
    {
        this._client = client;
        this._logger = logger;
        this._shutdownCts = CancellationTokenSource.CreateLinkedTokenSource(hostApplicationLifetime.ApplicationStopping);

        this._messageRouter = new GrpcMessageRouter(client, this, _clientId, logger, this._shutdownCts.Token);
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

    private Guid _clientId = Guid.NewGuid();
    private CallOptions CallOptions
    {
        get
        {
            var metadata = new Metadata
            {
                { "client-id", this._clientId.ToString() }
            };
            return new CallOptions(headers: metadata);
        }
    }

    public IProtoSerializationRegistry SerializationRegistry { get; } = new ProtobufSerializationRegistry();

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

        var agentId = request.Target;
        var agent = await this._agentsContainer.EnsureAgentAsync(agentId.FromProtobuf());

        // Convert payload back to object
        var payload = request.Payload;
        var message = payload.ToObject(SerializationRegistry);

        var messageContext = new MessageContext(request.RequestId, cancellationToken)
        {
            Sender = request.Source?.FromProtobuf() ?? null,
            Topic = null,
            IsRpc = true
        };

        var result = await agent.OnMessageAsync(message, messageContext);

        if (result is not null)
        {
            var response = new RpcResponse
            {
                RequestId = request.RequestId,
                Payload = result.ToPayload(SerializationRegistry)
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
            var message = payload.ToObject(SerializationRegistry);
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
        Contracts.AgentId? sender = null;
        if (evt.Attributes.TryGetValue(Constants.AGENT_SENDER_TYPE_ATTR, out var typeValue) && evt.Attributes.TryGetValue(Constants.AGENT_SENDER_KEY_ATTR, out var keyValue))
        {
            sender = new Contracts.AgentId
            {
                Type = typeValue.CeString,
                Key = keyValue.CeString
            };
        }

        var messageId = evt.Id;
        var typeName = evt.Attributes[Constants.DATA_SCHEMA_ATTR].CeString;
        var serializer = SerializationRegistry.GetSerializer(typeName) ?? throw new Exception();
        var message = serializer.Deserialize(evt.ProtoData);

        var messageContext = new MessageContext(messageId, cancellationToken)
        {
            Sender = sender,
            Topic = topic,
            IsRpc = false
        };

        // Iterate over subscriptions values to find receiving agents
        foreach (var subscription in this._agentsContainer.Subscriptions.Values)
        {
            if (subscription.Matches(topic))
            {
                var recipient = subscription.MapToAgent(topic);
                var agent = await this._agentsContainer.EnsureAgentAsync(recipient);
                await agent.OnMessageAsync(message, messageContext);
            }
        }
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

    public async ValueTask<object?> SendMessageAsync(object message, Contracts.AgentId recepient, Contracts.AgentId? sender = null, string? messageId = null, CancellationToken cancellationToken = default)
    {
        if (!SerializationRegistry.Exists(message.GetType()))
        {
            SerializationRegistry.RegisterSerializer(message.GetType());
        }

        var payload = message.ToPayload(SerializationRegistry);
        var request = new RpcRequest
        {
            RequestId = Guid.NewGuid().ToString(),
            Source = sender?.ToProtobuf() ?? null,
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

    public async ValueTask PublishMessageAsync(object message, TopicId topic, Contracts.AgentId? sender = null, string? messageId = null, CancellationToken cancellationToken = default)
    {
        if (!SerializationRegistry.Exists(message.GetType()))
        {
            SerializationRegistry.RegisterSerializer(message.GetType());
        }
        var protoAny = (SerializationRegistry.GetSerializer(message.GetType()) ?? throw new Exception()).Serialize(message);
        var typeName = SerializationRegistry.TypeNameResolver.ResolveTypeName(message.GetType());

        var cloudEvent = CloudEventExtensions.CreateCloudEvent(protoAny, topic, typeName, sender, messageId ?? Guid.NewGuid().ToString());

        Message msg = new()
        {
            CloudEvent = cloudEvent
        };

        await this._messageRouter.RouteMessageAsync(msg, cancellationToken);
    }

    public ValueTask<Contracts.AgentId> GetAgentAsync(Contracts.AgentId agentId, bool lazy = true) => this._agentsContainer.GetAgentAsync(agentId, lazy);

    public ValueTask<Contracts.AgentId> GetAgentAsync(AgentType agentType, string key = "default", bool lazy = true)
        => this.GetAgentAsync(new Contracts.AgentId(agentType, key), lazy);

    public ValueTask<Contracts.AgentId> GetAgentAsync(string agent, string key = "default", bool lazy = true)
        => this.GetAgentAsync(new Contracts.AgentId(agent, key), lazy);

    public async ValueTask<IDictionary<string, JsonElement>> SaveAgentStateAsync(Contracts.AgentId agentId)
    {
        IHostableAgent agent = await this._agentsContainer.EnsureAgentAsync(agentId);
        return await agent.SaveStateAsync();
    }

    public async ValueTask LoadAgentStateAsync(Contracts.AgentId agentId, IDictionary<string, JsonElement> state)
    {
        IHostableAgent agent = await this._agentsContainer.EnsureAgentAsync(agentId);
        await agent.LoadStateAsync(state);
    }

    public async ValueTask<AgentMetadata> GetAgentMetadataAsync(Contracts.AgentId agentId)
    {
        IHostableAgent agent = await this._agentsContainer.EnsureAgentAsync(agentId);
        return agent.Metadata;
    }

    public async ValueTask AddSubscriptionAsync(ISubscriptionDefinition subscription)
    {
        this._agentsContainer.AddSubscription(subscription);

        var _ = await this._client.AddSubscriptionAsync(new AddSubscriptionRequest
        {
            Subscription = subscription.ToProtobuf()
        }, this.CallOptions);
    }

    public async ValueTask RemoveSubscriptionAsync(string subscriptionId)
    {
        this._agentsContainer.RemoveSubscriptionAsync(subscriptionId);

        await this._client.RemoveSubscriptionAsync(new RemoveSubscriptionRequest
        {
            Id = subscriptionId
        }, this.CallOptions);
    }

    public async ValueTask<AgentType> RegisterAgentFactoryAsync(AgentType type, Func<Contracts.AgentId, IAgentRuntime, ValueTask<IHostableAgent>> factoryFunc)
    {
        this._agentsContainer.RegisterAgentFactory(type, factoryFunc);

        await this._client.RegisterAgentAsync(new RegisterAgentTypeRequest
        {
            Type = type,
        }, this.CallOptions);

        return type;
    }

    public ValueTask<AgentProxy> TryGetAgentProxyAsync(Contracts.AgentId agentId)
    {
        // TODO: Do we want to support getting remote agent proxies?
        return ValueTask.FromResult(new AgentProxy(agentId, this));
    }

    public async ValueTask LoadStateAsync(IDictionary<string, JsonElement> state)
    {
        HashSet<AgentType> registeredTypes = this._agentsContainer.RegisteredAgentTypes;

        foreach (var agentIdStr in state.Keys)
        {
            Contracts.AgentId agentId = Contracts.AgentId.FromStr(agentIdStr);

            if (state[agentIdStr].ValueKind != JsonValueKind.Object)
            {
                throw new Exception($"Agent state for {agentId} is not a valid JSON object.");
            }

            var agentState = JsonSerializer.Deserialize<IDictionary<string, JsonElement>>(state[agentIdStr].GetRawText())
                             ?? throw new Exception($"Failed to deserialize state for {agentId}.");

            if (registeredTypes.Contains(agentId.Type))
            {
                IHostableAgent agent = await this._agentsContainer.EnsureAgentAsync(agentId);
                await agent.LoadStateAsync(agentState);
            }
        }
    }

    public async ValueTask<IDictionary<string, JsonElement>> SaveStateAsync()
    {
        Dictionary<string, JsonElement> state = new();
        foreach (var agent in this._agentsContainer.LiveAgents)
        {
            var agentState = await agent.SaveStateAsync();
            state[agent.Id.ToString()] = JsonSerializer.SerializeToElement(agentState);
        }
        return state;
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

