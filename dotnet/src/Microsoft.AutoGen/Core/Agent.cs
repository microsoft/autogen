
// Copyright (c) Microsoft Corporation. All rights reserved.
// Agent.cs

using System.Collections.Concurrent;
using System.Diagnostics;
using System.Reflection;
using System.Text;
using System.Text.Json;
using System.Threading.Channels;
using Google.Protobuf;
using Microsoft.AutoGen.Contracts;
using Microsoft.Extensions.Logging;

namespace Microsoft.AutoGen.Core;
/// <summary>
/// Represents the base class for an agent in the AutoGen system.
/// </summary>
public abstract class Agent
{
    private readonly object _lock = new();
    private readonly ConcurrentDictionary<string, TaskCompletionSource<RpcResponse>> _pendingRequests = [];

    /// <summary>
    /// The activity source for tracing.
    /// </summary>
    public static readonly ActivitySource s_source = new("Microsoft.AutoGen.Core.Agent");

    /// <summary>
    /// Gets the unique identifier of the agent.
    /// </summary>
    public AgentId AgentId { get; private set; }
    private readonly Channel<object> _mailbox = Channel.CreateUnbounded<object>();
    protected internal ILogger<Agent> _logger;
    public IAgentWorker Worker { get; private set; }
    private readonly ConcurrentDictionary<Type, MethodInfo> _handlersByMessageType;
    protected readonly AgentsMetadata EventTypes;

    protected Agent(
        AgentsMetadata eventTypes,
        ILogger<Agent>? logger = null)
    {
        EventTypes = eventTypes;
        AgentId = new AgentId(this.GetType().Name, Guid.NewGuid().ToString());
        _logger = logger ?? LoggerFactory.Create(builder => { }).CreateLogger<Agent>();
        _handlersByMessageType = new(GetType().GetHandlersLookupTable());
        Worker = new UninitializedAgentWorker();
    }
    public static void Initialize(IAgentWorker worker, Agent agent)
    {
        agent.Worker = worker;
        agent.Start();
        agent.AddImplicitSubscriptionsAsync().AsTask().Wait();
    }

    private async ValueTask AddImplicitSubscriptionsAsync()
    {
        var topicTypes = new List<string>
        {
            this.AgentId.Type + ":" + this.AgentId.Key,
            this.AgentId.Type
        };

        foreach (var topicType in topicTypes)
        {
            var subscriptionRequest = new AddSubscriptionRequest
            {
                RequestId = Guid.NewGuid().ToString(),
                Subscription = new Subscription
                {
                    TypeSubscription = new TypeSubscription
                    {
                        AgentType = this.AgentId.Type,
                        TopicType = topicType
                    }
                }
            };
            // explicitly wait for this to complete
            Worker.SubscribeAsync(subscriptionRequest).AsTask().Wait();
        }

        // using reflection, find all methods that Handle<T> and subscribe to the topic T
        var handleMethods = this.GetType().GetMethods().Where(m => m.Name == "Handle").ToList();
        foreach (var method in handleMethods)
        {
            var eventType = method.GetParameters()[0].ParameterType;
            var topics = EventTypes.GetTopicsForAgent(GetType());
            if (topics != null)
            {
                foreach (var topic in topics)
                {
                    await SubscribeAsync(topic).ConfigureAwait(true);
                }
            }
        }
    }

    /// <summary>
    /// Starts the message pump for the agent.
    /// </summary>
    /// <returns>A task representing the asynchronous operation.</returns>
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
    public void ReceiveMessage(Message message) => _mailbox.Writer.TryWrite(message);

    private async Task RunMessagePump()
    {
        await Task.CompletedTask.ConfigureAwait(ConfigureAwaitOptions.ForceYielding);
        await foreach (var message in _mailbox.Reader.ReadAllAsync())
        {
            try
            {
                switch (message)
                {
                    case Message msg:
                        await HandleRpcMessage(msg, new CancellationToken()).ConfigureAwait(false);
                        break;
                    default:
                        throw new InvalidOperationException($"Unexpected message '{message}'.");
                }
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error processing message.");
            }
        }
    }
    protected internal async Task HandleRpcMessage(Message msg, CancellationToken cancellationToken = default)
    {
        switch (msg.MessageCase)
        {
            case Message.MessageOneofCase.CloudEvent:
                {
                    var activity = this.ExtractActivity(msg.CloudEvent.Type, msg.CloudEvent.Attributes);
                    await this.InvokeWithActivityAsync(
                        static ((Agent Agent, CloudEvent Item) state, CancellationToken ct) => state.Agent.CallHandlerAsync(state.Item, ct),
                        (this, msg.CloudEvent),
                        activity,
                        msg.CloudEvent.Type, cancellationToken).ConfigureAwait(false);
                }
                break;
            case Message.MessageOneofCase.Request:
                {
                    var activity = this.ExtractActivity(msg.Request.Method, msg.Request.Metadata);
                    await this.InvokeWithActivityAsync(
                        static ((Agent Agent, RpcRequest Request) state, CancellationToken ct) => state.Agent.OnRequestCoreAsync(state.Request, ct),
                        (this, msg.Request),
                        activity,
                        msg.Request.Method, cancellationToken).ConfigureAwait(false);
                }
                break;
            case Message.MessageOneofCase.Response:
                OnResponseCore(msg.Response);
                break;
        }
    }
    public async ValueTask<List<Subscription>> GetSubscriptionsAsync()
    {
        GetSubscriptionsRequest request = new();
        return await Worker.GetSubscriptionsAsync(request).ConfigureAwait(false);
    }
    public async ValueTask<AddSubscriptionResponse> SubscribeAsync(string topic)
    {
        AddSubscriptionRequest subscriptionRequest = new()
        {
            RequestId = Guid.NewGuid().ToString(),
            Subscription = new Subscription
            {
                TypeSubscription = new TypeSubscription
                {
                    TopicType = topic,
                    AgentType = this.AgentId.Type
                }
            }
        };
        var subscriptionResponse = await Worker.SubscribeAsync(subscriptionRequest).ConfigureAwait(true);
        if (!subscriptionResponse.Success)
        {
            _logger.LogError($"{GetType}{AgentId.Key}: Failed to unsubscribe from topic {topic}");
        }
        return subscriptionResponse;
    }
    public async ValueTask<RemoveSubscriptionResponse> UnsubscribeAsync(Guid id)
    {
        RemoveSubscriptionRequest subscriptionRequest = new()
        {
            Id = id.ToString()
        };
        var subscriptionResponse = await Worker.UnsubscribeAsync(subscriptionRequest).ConfigureAwait(true);
        if (!subscriptionResponse.Success)
        {
            _logger.LogError($"{GetType}{AgentId.Key}: Failed to unsubscribe from Subscription {id}");
        }
        return subscriptionResponse;
    }
    public async ValueTask<RemoveSubscriptionResponse> UnsubscribeAsync(string topic)
    {
        var subscriptions = await GetSubscriptionsAsync().ConfigureAwait(false);
        var subscription = subscriptions.FirstOrDefault(s => s.TypeSubscription.TopicType == topic);
        if (subscription == null)
        {
            var error = $"{GetType}{AgentId.Key}: Subscription not found for topic {topic}";
            _logger.LogError(error);
            return new RemoveSubscriptionResponse { Success = false, Error = error };
        }
        var id = Guid.Parse(subscription.Id);
        return await UnsubscribeAsync(id).ConfigureAwait(true);
    }
    public async Task StoreAsync(AgentState state, CancellationToken cancellationToken = default)
    {
        await Worker.StoreAsync(state, cancellationToken).ConfigureAwait(false);
        return;
    }
    public async Task<T> ReadAsync<T>(AgentId agentId, CancellationToken cancellationToken = default) where T : IMessage, new()
    {
        var agentstate = await Worker.ReadAsync(agentId, cancellationToken).ConfigureAwait(false);
        return agentstate.FromAgentState<T>();
    }
    private void OnResponseCore(RpcResponse response)
    {
        var requestId = response.RequestId;
        TaskCompletionSource<RpcResponse>? completion;
        lock (_lock)
        {
            if (!_pendingRequests.Remove(requestId, out completion))
            {
                throw new InvalidOperationException($"Unknown request id '{requestId}'.");
            }
        }

        completion.SetResult(response);
    }
    private async Task OnRequestCoreAsync(RpcRequest request, CancellationToken cancellationToken = default)
    {
        RpcResponse response;

        try
        {
            response = await HandleRequestAsync(request).ConfigureAwait(false);
        }
        catch (Exception ex)
        {
            response = new RpcResponse { Error = ex.Message };
        }
        response.RequestId = request.RequestId;

        await Worker.SendResponseAsync(response, cancellationToken).ConfigureAwait(false);
    }

    protected async Task<RpcResponse> RequestAsync(AgentId target, string method, Dictionary<string, string> parameters)
    {
        var requestId = Guid.NewGuid().ToString();
        var request = new RpcRequest
        {
            Target = target,
            RequestId = requestId,
            Method = method,
            Payload = new Payload
            {
                DataType = "application/json",
                Data = ByteString.CopyFrom(JsonSerializer.Serialize(parameters), Encoding.UTF8),
                DataContentType = "application/json"

            }
        };

        var activity = s_source.StartActivity($"Call '{method}'", ActivityKind.Client, Activity.Current?.Context ?? default);
        activity?.SetTag("peer.service", target.ToString());

        var completion = new TaskCompletionSource<RpcResponse>(TaskCreationOptions.RunContinuationsAsynchronously);
        IAgentWorkerExtensions.Update(this.Worker, request, activity);
        await this.InvokeWithActivityAsync(
            static async (state, ct) =>
            {
                var (self, request, completion) = state;

                self._pendingRequests.AddOrUpdate(request.RequestId, _ => completion, (_, __) => completion);

                await state.Item1.Worker!.SendRequestAsync(state.Item1, state.request, ct).ConfigureAwait(false);

                await completion.Task.ConfigureAwait(false);
            },
            (this, request, completion),
            activity,
            method).ConfigureAwait(false);

        // Return the result from the already-completed task
        return await completion.Task.ConfigureAwait(false);
    }

    private string SetTopic(string? topic = null, string? source = null, string? key = null)
    {
        if (string.IsNullOrWhiteSpace(topic))
        {
            topic = this.AgentId.Type + "." + this.AgentId.Key;
        }
        else
        {
            topic = topic + "." + source + "." + key;
        }
        return topic;
    }

    /// <summary>
    /// Publishes a message asynchronously.
    /// </summary>
    /// <typeparam name="T">The type of the message.</typeparam>
    /// <param name="token">A token to cancel the operation.</param>
    /// <returns>A task representing the asynchronous operation.</returns>
    public async ValueTask PublishMessageAsync<T>(T message, string topic, string source, string key, CancellationToken token = default) where T : IMessage
    {
        // if there are no topic types, use the agent's default topic subscription attribute and the agent's type and key
        if (string.IsNullOrWhiteSpace(topic))
        {
            if (string.IsNullOrWhiteSpace(topic))
            {
                topic = this.AgentId.Type + "." + this.AgentId.Key;
            }
            else
            {
                topic = topic + "." + source + "." + key;
            }

            var topicTypes = this.GetType().GetCustomAttributes<TopicSubscriptionAttribute>().Select(t => t.Topic);
            if (!topicTypes.Any())
            {
                topicTypes = topicTypes.Append(string.IsNullOrWhiteSpace(source) ? this.AgentId.Type + "." + this.AgentId.Key : source);
            }
            topicTypes = topicTypes.Append(SetTopic(topic, source, key));
            foreach (var t in topicTypes)
            {
                await PublishEventAsync(t, message, token).ConfigureAwait(false);
            }
        }
        else
        {
            await PublishEventAsync(topic, message, token).ConfigureAwait(false);
        }
    }
    public async ValueTask PublishMessageAsync<T>(T message, string topic, string source, CancellationToken token = default) where T : IMessage
    {
        string key = this.AgentId.Key;
        await PublishMessageAsync(message, topic, source, key, token).ConfigureAwait(false);
    }
    public async ValueTask PublishMessageAsync<T>(T message, string topic, CancellationToken token = default) where T : IMessage
    {
        string source = this.AgentId.Type;
        string key = this.AgentId.Key;
        await PublishMessageAsync(message, topic, source, key, token).ConfigureAwait(false);
    }
    public async ValueTask PublishMessageAsync<T>(T message, CancellationToken token = default) where T : IMessage
    {
        string topic = "";
        string source = this.AgentId.Type;
        string key = this.AgentId.Key;
        await PublishMessageAsync(message, topic, source, key, token).ConfigureAwait(false);
    }
    public async ValueTask PublishEventAsync(string topic, IMessage message, CancellationToken cancellationToken = default)
    {
        await PublishEventAsync(message.ToCloudEvent(key: GetType().Name, topic: topic), cancellationToken).ConfigureAwait(false);
    }
    public async ValueTask PublishEventAsync(CloudEvent item, CancellationToken cancellationToken = default)
    {
        var activity = s_source.StartActivity($"PublishEventAsync '{item.Type}'", ActivityKind.Client, Activity.Current?.Context ?? default);
        activity?.SetTag("peer.service", $"{item.Type}/{item.Source}");

        // TODO: fix activity
        IAgentWorkerExtensions.Update(this.Worker, item, activity);
        await this.InvokeWithActivityAsync(
            static async ((Agent Agent, CloudEvent Event) state, CancellationToken ct) =>
            {
                await state.Agent.Worker.PublishEventAsync(state.Event).ConfigureAwait(false);
            },
            (this, item),
            activity,
            item.Type, cancellationToken).ConfigureAwait(false);
    }

    public Task CallHandlerAsync(CloudEvent item, CancellationToken cancellationToken = default)
    {
        // Only send the event to the handler if the agent type is handling that type
        if (EventTypes.CheckIfTypeHandles(GetType(), eventName: item.Type))
        {
            var payload = item.ProtoData.Unpack(EventTypes.TypeRegistry);
            var eventType = EventTypes.GetEventTypeByName(item.Type);
            if (eventType == null)
            {
                _logger.LogError($"Event type {item.Type} not found in the registry");
                return Task.CompletedTask;
            }
            var convertedPayload = Convert.ChangeType(payload, eventType);
            var genericInterfaceType = typeof(IHandle<>).MakeGenericType(eventType);

            MethodInfo methodInfo;
            try
            {
                // check that our target actually implements this interface, otherwise call the default static
                if (genericInterfaceType.IsAssignableFrom(this.GetType()))
                {
                    methodInfo = genericInterfaceType.GetMethod(nameof(IHandle<IMessage>.Handle), BindingFlags.Public | BindingFlags.Instance)
                                    ?? throw new InvalidOperationException($"Method not found on type {genericInterfaceType.FullName}");
                    return methodInfo.Invoke(this, new object[] { convertedPayload, cancellationToken }) as Task ?? Task.CompletedTask;
                }
                else
                {
                    // The error here is we have registered for an event that we do not have code to listen to
                    throw new InvalidOperationException($"Agent Type '{GetType()}' is registered to handle this type but no handler found for event '{item.Type}'; expecting IHandle<{item.Type}> implementation.");
                }
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, $"Error invoking method {nameof(IHandle<IMessage>.Handle)}");
                throw; // TODO: ?
            }
        }
        return Task.CompletedTask;
    }

    public Task<RpcResponse> HandleRequestAsync(RpcRequest request) => Task.FromResult(new RpcResponse { Error = "Not implemented" });

    /// <summary>
    /// Handles a generic object
    /// </summary>
    /// <param name="item">The object to handle</param>
    /// <param name="cancellationToken">The cancellation token</param>
    /// <returns>A task representing the asynchronous operation.</returns>
    /// TODO: this is only called from tests, should we remove it?
    public virtual async Task HandleObjectAsync(object item, CancellationToken cancellationToken = default)
    {
        // get all Handle<T> methods
        var handleTMethods = this.GetType().GetMethods().Where(m => m.Name == "Handle" && m.GetParameters().Length == 1).ToList();
        // get the one that matches the type of the item
        var handleTMethod = handleTMethods.FirstOrDefault(m => m.GetParameters()[0].ParameterType == item.GetType());
        // if we found one, invoke it
        if (handleTMethod != null)
        {
            await (Task)handleTMethod.Invoke(this, [item])!;
        }
        // otherwise, complain
        _logger.LogError($"No handler found for type {item.GetType().FullName}");
    }
}
