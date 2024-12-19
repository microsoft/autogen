
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
public abstract class Agent : IHandle
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
    public AgentMessenger Messenger { get; private set; }
    private readonly ConcurrentDictionary<Type, MethodInfo> _handlersByMessageType;
    internal Task Completion { get; private set; }

    protected readonly EventTypes EventTypes;

    protected Agent(IAgentWorker worker,
        EventTypes eventTypes,
        ILogger<Agent>? logger = null)
    {
        EventTypes = eventTypes;
        AgentId = new AgentId(this.GetType().Name, new Guid().ToString());
        _logger = logger ?? LoggerFactory.Create(builder => { }).CreateLogger<Agent>();
        _handlersByMessageType = new(GetType().GetHandlersLookupTable());
        Messenger = AgentMessengerFactory.Create(worker, DistributedContextPropagator.Current);
        AddImplicitSubscriptionsAsync().AsTask().Wait();
        Completion = Start();
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
            await Messenger.SendMessageAsync(new Message { AddSubscriptionRequest = subscriptionRequest }).ConfigureAwait(true);
        }

        // using reflection, find all methods that Handle<T> and subscribe to the topic T
        var handleMethods = this.GetType().GetMethods().Where(m => m.Name == "Handle").ToList();
        foreach (var method in handleMethods)
        {
            var eventType = method.GetParameters()[0].ParameterType;
            var topic = EventTypes.EventsMap.FirstOrDefault(x => x.Value.Contains(eventType.Name)).Key;
            if (topic != null)
            {
                Subscribe(nameof(topic));
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
                        static ((Agent Agent, CloudEvent Item) state, CancellationToken _) => state.Agent.CallHandler(state.Item),
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
    public List<string> Subscribe(string topic)
    {
        Message message = new()
        {
            AddSubscriptionRequest = new()
            {
                RequestId = Guid.NewGuid().ToString(),
                Subscription = new Subscription
                {
                    TypeSubscription = new TypeSubscription
                    {
                        TopicType = topic,
                        AgentType = this.AgentId.Key
                    }
                }
            }
        };
        Messenger.SendMessageAsync(message).AsTask().Wait();

        return new List<string> { topic };
    }
    public async Task StoreAsync(AgentState state, CancellationToken cancellationToken = default)
    {
        await Messenger.StoreAsync(state, cancellationToken).ConfigureAwait(false);
        return;
    }
    public async Task<T> ReadAsync<T>(AgentId agentId, CancellationToken cancellationToken = default) where T : IMessage, new()
    {
        var agentstate = await Messenger.ReadAsync(agentId, cancellationToken).ConfigureAwait(false);
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
        await Messenger.SendResponseAsync(request, response, cancellationToken).ConfigureAwait(false);
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
        Messenger!.Update(request, activity);
        await this.InvokeWithActivityAsync(
            static async (state, ct) =>
            {
                var (self, request, completion) = state;

                self._pendingRequests.AddOrUpdate(request.RequestId, _ => completion, (_, __) => completion);

                await state.Item1.Messenger!.SendRequestAsync(state.Item1, state.request, ct).ConfigureAwait(false);

                await completion.Task.ConfigureAwait(false);
            },
            (this, request, completion),
            activity,
            method).ConfigureAwait(false);

        // Return the result from the already-completed task
        return await completion.Task.ConfigureAwait(false);
    }

    public async ValueTask PublishMessageAsync<T>(T message, string? source = null, CancellationToken token = default) where T : IMessage
    {
        var src = string.IsNullOrWhiteSpace(source) ? this.AgentId.Key : source;
        var evt = message.ToCloudEvent(src);
        await PublishEventAsync(evt, token).ConfigureAwait(false);
    }

    public async ValueTask PublishEventAsync(CloudEvent item, CancellationToken cancellationToken = default)
    {
        var activity = s_source.StartActivity($"PublishEventAsync '{item.Type}'", ActivityKind.Client, Activity.Current?.Context ?? default);
        activity?.SetTag("peer.service", $"{item.Type}/{item.Source}");

        // TODO: fix activity
        Messenger.Update(item, activity);
        await this.InvokeWithActivityAsync(
            static async ((Agent Agent, CloudEvent Event) state, CancellationToken ct) =>
            {
                await state.Agent.Messenger.PublishEventAsync(state.Event).ConfigureAwait(false);
            },
            (this, item),
            activity,
            item.Type, cancellationToken).ConfigureAwait(false);
    }

    public Task CallHandler(CloudEvent item)
    {
        // Only send the event to the handler if the agent type is handling that type
        // foreach of the keys in the EventTypes.EventsMap[] if it contains the item.type
        foreach (var key in EventTypes.EventsMap.Keys)
        {
            if (EventTypes.EventsMap[key].Contains(item.Type))
            {
                var payload = item.ProtoData.Unpack(EventTypes.TypeRegistry);
                var convertedPayload = Convert.ChangeType(payload, EventTypes.Types[item.Type]);
                var genericInterfaceType = typeof(IHandle<>).MakeGenericType(EventTypes.Types[item.Type]);

                MethodInfo methodInfo;
                try
                {
                    // check that our target actually implements this interface, otherwise call the default static
                    if (genericInterfaceType.IsAssignableFrom(this.GetType()))
                    {
                        methodInfo = genericInterfaceType.GetMethod(nameof(IHandle<object>.Handle), BindingFlags.Public | BindingFlags.Instance)
                                       ?? throw new InvalidOperationException($"Method not found on type {genericInterfaceType.FullName}");
                        return methodInfo.Invoke(this, [payload]) as Task ?? Task.CompletedTask;
                    }
                    else
                    {
                        // The error here is we have registered for an event that we do not have code to listen to
                        throw new InvalidOperationException($"No handler found for event '{item.Type}'; expecting IHandle<{item.Type}> implementation.");
                    }
                }
                catch (Exception ex)
                {
                    _logger.LogError(ex, $"Error invoking method {nameof(IHandle<object>.Handle)}");
                    throw; // TODO: ?
                }
            }
        }

        return Task.CompletedTask;
    }

    public Task<RpcResponse> HandleRequestAsync(RpcRequest request) => Task.FromResult(new RpcResponse { Error = "Not implemented" });

    //TODO: should this be async and cancellable?
    public virtual Task HandleObject(object item)
    {
        // get all Handle<T> methods
        var handleTMethods = this.GetType().GetMethods().Where(m => m.Name == "Handle" && m.GetParameters().Length == 1).ToList();

        // get the one that matches the type of the item
        var handleTMethod = handleTMethods.FirstOrDefault(m => m.GetParameters()[0].ParameterType == item.GetType());

        // if we found one, invoke it
        if (handleTMethod != null)
        {
            return (Task)handleTMethod.Invoke(this, [item])!;
        }

        // otherwise, complain
        throw new InvalidOperationException($"No handler found for type {item.GetType().FullName}");
    }
    public async ValueTask PublishEventAsync(string topic, IMessage evt, CancellationToken cancellationToken = default)
    {
        await PublishEventAsync(evt.ToCloudEvent(topic), cancellationToken).ConfigureAwait(false);
    }
}
