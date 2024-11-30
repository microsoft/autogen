// Copyright (c) Microsoft Corporation. All rights reserved.
// AgentBase.cs

using System.Collections.Concurrent;
using System.Diagnostics;
using System.Reflection;
using System.Text;
using System.Text.Json;
using System.Threading.Channels;
using Google.Protobuf;
using Microsoft.AutoGen.Abstractions;
using Microsoft.Extensions.Logging;

namespace Microsoft.AutoGen.Core;

/// <summary>
/// Represents the base class for an agent in the AutoGen system.
/// </summary>
public abstract class AgentBase
{
    /// <summary>
    /// The activity source for tracing.
    /// </summary>
    public static readonly ActivitySource s_source = new("AutoGen.Agent");

    /// <summary>
    /// Gets the unique identifier of the agent.
    /// </summary>
    public AgentId AgentId => _context.AgentId;

    private readonly object _lock = new();
    private readonly ConcurrentDictionary<string, TaskCompletionSource<RpcResponse>> _pendingRequests = new();

    private readonly Channel<object> _mailbox = Channel.CreateUnbounded<object>();
    private readonly RuntimeContext _context;

    /// <summary>
    /// Gets the runtime context of the agent.
    /// </summary>
    public RuntimeContext Context => _context;

    /// <summary>
    /// Gets or sets the route of the agent.
    /// </summary>
    public string Route { get; set; } = "base";

    protected internal ILogger<AgentBase> _logger;
    protected readonly EventTypes EventTypes;

    /// <summary>
    /// Initializes a new instance of the <see cref="AgentBase"/> class.
    /// </summary>
    /// <param name="context">The runtime context of the agent.</param>
    /// <param name="eventTypes">The event types associated with the agent.</param>
    /// <param name="logger">The logger instance for logging.</param>
    protected AgentBase(
        RuntimeContext context,
        EventTypes eventTypes,
        ILogger<AgentBase>? logger = null)
    {
        _context = context;
        context.AgentInstance = this;
        EventTypes = eventTypes;
        _logger = logger ?? LoggerFactory.Create(builder => { }).CreateLogger<AgentBase>();
        
        Completion = Start();
    }

    /// <summary>
    /// Gets the task representing the completion of the agent's operations.
    /// </summary>
    internal Task Completion { get; }

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

    /// <summary>
    /// Receives a message and writes it to the mailbox.
    /// </summary>
    /// <param name="message">The message to receive.</param>
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

    /// <summary>
    /// Handles an RPC message.
    /// </summary>
    /// <param name="msg">The message to handle.</param>
    /// <param name="cancellationToken">A token to cancel the operation.</param>
    /// <returns>A task representing the asynchronous operation.</returns>
    protected internal async Task HandleRpcMessage(Message msg, CancellationToken cancellationToken = default)
    {
        switch (msg.MessageCase)
        {
            case Message.MessageOneofCase.CloudEvent:
                {
                    var activity = this.ExtractActivity(msg.CloudEvent.Type, msg.CloudEvent.Metadata);
                    await this.InvokeWithActivityAsync(
                        static (state, ct) => state.Item1.CallHandler(state.CloudEvent, ct),
                        (this, msg.CloudEvent),
                        activity,
                        msg.CloudEvent.Type, cancellationToken).ConfigureAwait(false);
                }
                break;
            case Message.MessageOneofCase.Request:
                {
                    var activity = this.ExtractActivity(msg.Request.Method, msg.Request.Metadata);
                    await this.InvokeWithActivityAsync(
                        static (state, ct) => state.Item1.OnRequestCoreAsync(state.Request, ct),
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

    /// <summary>
    /// Subscribes to a topic.
    /// </summary>
    /// <param name="topic">The topic to subscribe to.</param>
    /// <returns>A list of subscribed topics.</returns>
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
                        AgentType = AgentId.Key
                    }
                }
            }
        };
        _context.SendMessageAsync(message).AsTask().Wait();

        return new List<string> { topic };
    }

    /// <summary>
    /// Stores the agent state asynchronously.
    /// </summary>
    /// <param name="state">The agent state to store.</param>
    /// <param name="cancellationToken">A token to cancel the operation.</param>
    /// <returns>A task representing the asynchronous operation.</returns>
    public async Task StoreAsync(AgentState state, CancellationToken cancellationToken = default)
    {
        await _context.StoreAsync(state, cancellationToken).ConfigureAwait(false);
    }

    /// <summary>
    /// Reads the agent state asynchronously.
    /// </summary>
    /// <typeparam name="T">The type of the agent state.</typeparam>
    /// <param name="agentId">The ID of the agent whose state is to be read.</param>
    /// <param name="cancellationToken">A token to cancel the operation.</param>
    /// <returns>A task representing the asynchronous operation, containing the agent state.</returns>
    public async Task<T> ReadAsync<T>(AgentId agentId, CancellationToken cancellationToken = default) where T : IMessage, new()
    {
        var agentState = await _context.ReadAsync(agentId, cancellationToken).ConfigureAwait(false);
        return agentState.FromAgentState<T>();
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

    private async Task OnRequestCoreAsync(RpcRequest request, CancellationToken cancellationToken)
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
        await _context.SendResponseAsync(request, response, cancellationToken).ConfigureAwait(false);
    }

    /// <summary>
    /// Sends a request asynchronously.
    /// </summary>
    /// <param name="target">The target agent ID.</param>
    /// <param name="method">The method to call.</param>
    /// <param name="parameters">The parameters for the method.</param>
    /// <returns>A task representing the asynchronous operation, containing the RPC response.</returns>
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
        _context.Update(request, activity);
        await this.InvokeWithActivityAsync(
            static async (state, ct) =>
            {
                var (self, request, completion) = state;

                lock (self._lock)
                {
                    self._pendingRequests[request.RequestId] = completion;
                }

                await state.Item1._context.SendRequestAsync(state.Item1, state.request, ct).ConfigureAwait(false);

                await completion.Task.ConfigureAwait(false);
            },
            (this, request, completion),
            activity,
            method).ConfigureAwait(false);

        // Return the result from the already-completed task
        return await completion.Task.ConfigureAwait(false);
    }

    /// <summary>
    /// Publishes a message asynchronously.
    /// </summary>
    /// <typeparam name="T">The type of the message.</typeparam>
    /// <param name="message">The message to publish.</param>
    /// <param name="source">The source of the message.</param>
    /// <param name="token">A token to cancel the operation.</param>
    /// <returns>A task representing the asynchronous operation.</returns>
    public async ValueTask PublishMessageAsync<T>(T message, string? source = null, CancellationToken token = default) where T : IMessage
    {
        var src = string.IsNullOrWhiteSpace(source) ? AgentId.Key : source;
        var evt = message.ToCloudEvent(src);
        await PublishEventAsync(evt, token).ConfigureAwait(false);
    }

    /// <summary>
    /// Publishes a cloud event asynchronously.
    /// </summary>
    /// <param name="item">The cloud event to publish.</param>
    /// <param name="cancellationToken">A token to cancel the operation.</param>
    /// <returns>A task representing the asynchronous operation.</returns>
    public async ValueTask PublishEventAsync(CloudEvent item, CancellationToken cancellationToken = default)
    {
        var activity = s_source.StartActivity($"PublishEventAsync '{item.Type}'", ActivityKind.Client, Activity.Current?.Context ?? default);
        activity?.SetTag("peer.service", $"{item.Type}/{item.Source}");

        // TODO: fix activity
        _context.Update(item, activity);
        await this.InvokeWithActivityAsync(
            static async (state, ct) =>
            {
                await state.Item1._context.PublishEventAsync(state.item, cancellationToken: ct).ConfigureAwait(false);
            },
            (this, item),
            activity,
            item.Type, cancellationToken).ConfigureAwait(false);
    }

    /// <summary>
    /// Calls the handler for a cloud event.
    /// </summary>
    /// <param name="item">The cloud event to handle.</param>
    /// <param name="cancellationToken">A token to cancel the operation.</param>
    /// <returns>A task representing the asynchronous operation.</returns>
    public Task CallHandler(CloudEvent item, CancellationToken cancellationToken)
    {
        // Only send the event to the handler if the agent type is handling that type
        // foreach of the keys in the EventTypes.EventsMap[] if it contains the item.type
        if (EventTypes.CheckIfTypeHandles(GetType(), item.Type) &&
                 item.Source == AgentId.Key)
        {
            var payload = item.ProtoData.Unpack(EventTypes.TypeRegistry);
            var eventType = EventTypes.GetEventTypeByName(item.Type) ?? throw new InvalidOperationException($"Type not found on event type {item.Type}");
            var convertedPayload = Convert.ChangeType(payload, eventType);
            var genericInterfaceType = typeof(IHandle<>).MakeGenericType(eventType);

            MethodInfo? methodInfo = null;
            try
            {
                // check that our target actually implements this interface, otherwise call the default static
                if (genericInterfaceType.IsInstanceOfType(this))
                {
                    methodInfo = genericInterfaceType.GetMethod("Handle", BindingFlags.Public | BindingFlags.Instance)
                                   ?? throw new InvalidOperationException($"Method not found on type {genericInterfaceType.FullName}");
                    return methodInfo.Invoke(this, new object[] { convertedPayload, cancellationToken }) as Task ?? Task.CompletedTask;
                }

                // The error here is we have registered for an event that we do not have code to listen to
                throw new InvalidOperationException($"No handler found for event '{item.Type}'; expecting IHandle<{item.Type}> implementation.");

            }
            catch (Exception ex)
            {
                _logger.LogError(ex, $"Error invoking method {methodInfo?.Name ?? "Handle"}");
                throw; // TODO: ?
            }
        }

        return Task.CompletedTask;
    }

    /// <summary>
    /// Handles an RPC request.
    /// </summary>
    /// <param name="request">The request to handle.</param>
    /// <param name="cancellationToken">A token to cancel the operation.</param>
    /// <returns>A task representing the asynchronous operation, containing the RPC response.</returns>
    public Task<RpcResponse> HandleRequestAsync(RpcRequest request, CancellationToken cancellationToken = default) => Task.FromResult(new RpcResponse { Error = "Not implemented" });


    /// <summary>
    /// Handles an object asynchronously by invoking the appropriate handler method based on the object's type.
    /// </summary>
    /// <param name="item">The object to handle.</param>
    /// <param name="cancellationToken">A token to cancel the operation.</param>
    /// <returns>A task representing the asynchronous operation.</returns>
    /// <exception cref="InvalidOperationException">Thrown when no handler is found for the object's type.</exception>
    public virtual Task HandleObjectAsync(object item, CancellationToken cancellationToken)
    {
        // get all Handle<T> methods
        var lookup = GetType().GetHandlersLookupTable();

        if (lookup.TryGetValue(item.GetType(), out var method))
        {
            if (method is null)
            {
                throw new InvalidOperationException($"No handler found for type {item.GetType().FullName}");
            }
            return (Task)method.Invoke(this, [item, cancellationToken])!;
        }

        throw new InvalidOperationException($"No handler found for type {item.GetType().FullName}");
    }

    /// <summary>
    /// Publishes a cloud event asynchronously.
    /// </summary>
    /// <param name="topic">The topic of the event.</param>
    /// <param name="evt">The event to publish.</param>
    /// <param name="cancellationToken">A token to cancel the operation.</param>
    /// <returns>A task representing the asynchronous operation.</returns>
    public async ValueTask PublishEventAsync(string topic, IMessage evt, CancellationToken cancellationToken = default)
    {
        await PublishEventAsync(evt.ToCloudEvent(topic), cancellationToken).ConfigureAwait(false);
    }
}
