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
    /// <summary>
    /// The activity source for tracing.
    /// </summary>
    public static readonly ActivitySource s_source = new("AutoGen.Agent");

    /// <summary>
    /// Gets the unique identifier of the agent.
    /// </summary>
    public AgentId AgentId => Context!.AgentId;

    private readonly ConcurrentDictionary<string, TaskCompletionSource<RpcResponse>> _pendingRequests = new();

    private readonly Channel<Message> _channel = Channel.CreateUnbounded<Message>();
 
    /// <summary>
    /// Gets the runtime context of the agent.
    /// </summary>
    public RuntimeContext? Context { get; private set; }

    /// <summary>
    /// Gets the task representing the completion of the agent's operations.
    /// </summary>
    internal Task? Completion { get; private set; }

    protected internal ILogger<Agent> _logger;
    protected readonly AgentsMetadata EventTypes;
    private readonly ConcurrentDictionary<Type, MethodInfo> _handlersByMessageType;
    private readonly CancellationTokenSource _agentCancelationSource = new();

   
    protected Agent(
        AgentsMetadata eventTypes,
        ILogger<Agent>? logger = null)
    {
        EventTypes = eventTypes;
        _logger = logger ?? LoggerFactory.Create(builder => { }).CreateLogger<Agent>();
        // get all Handle<T> methods
        _handlersByMessageType = new(GetType().GetHandlersLookupTable());
        Completion = Start();
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

    /// <summary>
    /// Receives a message and writes it to the mailbox.
    /// </summary>
    /// <param name="message">The message to receive.</param>
    public void ReceiveMessage(Message message) => _channel.Writer.TryWrite(message);

    private async Task RunMessagePump()
    {
        await Task.CompletedTask.ConfigureAwait(ConfigureAwaitOptions.ForceYielding);
        await foreach (var message in _channel.Reader.ReadAllAsync(_agentCancelationSource.Token))
        {
            try
            {
                await HandleRpcMessage(message, _agentCancelationSource.Token).ConfigureAwait(false);
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
                        static (state, ct) => state.Item1.HandleAsync(state.CloudEvent, ct),
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
    /// Stores the agent state asynchronously.
    /// </summary>
    /// <param name="state">The agent state to store.</param>
    /// <param name="cancellationToken">A token to cancel the operation.</param>
    /// <returns>A task representing the asynchronous operation.</returns>
    public async Task StoreAsync(AgentState state, CancellationToken cancellationToken = default)
    {
        await Context!.StoreAsync(state, cancellationToken).ConfigureAwait(false);
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
        var agentState = await Context!.ReadAsync(agentId, cancellationToken).ConfigureAwait(false);
        return agentState.FromAgentState<T>();
    }

    private void OnResponseCore(RpcResponse response)
    {
        var requestId = response.RequestId;
        if (!_pendingRequests.Remove(requestId, out var completion))
        {
            throw new InvalidOperationException($"Unknown request id '{requestId}'.");
        }

        completion.SetResult(response);
    }

    private async Task OnRequestCoreAsync(RpcRequest request, CancellationToken cancellationToken)
    {
        RpcResponse response;

        try
        {
            response = await HandleRequestAsync(request, cancellationToken).ConfigureAwait(false);
        }
        catch (Exception ex)
        {
            response = new RpcResponse { Error = ex.Message };
        }
        await Context!.SendResponseAsync(request, response, cancellationToken).ConfigureAwait(false);
    }

    /// <summary>
    /// Sends a request asynchronously.
    /// </summary>
    /// <param name="target">The target agent ID.</param>
    /// <param name="method">The method to call.</param>
    /// <param name="parameters">The parameters for the method.</param>
    /// <returns>A task representing the asynchronous operation, containing the RPC response.</returns>
    public async Task<RpcResponse> RequestAsync(AgentId target, string method, Dictionary<string, string> parameters)
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
        Context!.Update(request, activity);
        await this.InvokeWithActivityAsync(
            static async (state, ct) =>
            {
                var (self, request, completion) = state;

                self._pendingRequests.AddOrUpdate(request.RequestId, _ => completion, (_, __) => completion);

                await state.Item1.Context!.SendRequestAsync(state.Item1, state.request, ct).ConfigureAwait(false);

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
    /// <param name="event">The message to publish.</param>
    /// <param name="key">The source of the message.</param>
    /// <param name="token">A token to cancel the operation.</param>
    /// <returns>A task representing the asynchronous operation.</returns>
    public async ValueTask PublishEventAsync<T>(T @event, string? topic = null, string? key = null, CancellationToken token = default ) where T : IMessage
    {
        var k = string.IsNullOrWhiteSpace(key) ? AgentId.Key : key;
        var topicType = string.IsNullOrWhiteSpace(topic) ? "default" : topic;
        var evt = @event.ToCloudEvent(k, topicType);
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
        Context!.Update(item, activity);
        await this.InvokeWithActivityAsync(
            static async (state, ct) =>
            {
                await state.Item1.Context!.PublishEventAsync(state.item, cancellationToken: ct).ConfigureAwait(false);
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
    public Task HandleAsync(CloudEvent item, CancellationToken cancellationToken)
    {
        // Only send the event to the handler if the agent type is handling that type
        // foreach of the keys in the EventTypes.EventsMap[] if it contains the item.type
        var key = item.GetSubject();
        if (EventTypes.CheckIfTypeHandles(GetType(), item.Type) &&
                 key == AgentId.Key)
        {
            var payload = item.ProtoData.Unpack(EventTypes.TypeRegistry);
            var eventType = EventTypes.GetEventTypeByName(item.Type) ?? throw new InvalidOperationException($"Type not found on event type {item.Type}");
            var convertedPayload = Convert.ChangeType(payload, eventType);

            _handlersByMessageType.TryGetValue(eventType, out var methodInfo);
            if (methodInfo is null)
            {
                throw new InvalidOperationException($"No handler found for event '{item.Type}'; expecting IHandle<{item.Type}> implementation.");
            }

            try
            {
                // check that our target actually implements this interface, otherwise call the default static
                return methodInfo.Invoke(this, new object[] { convertedPayload, cancellationToken }) as Task ?? Task.CompletedTask;

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
    
    public void Dispose()
    {
        _agentCancelationSource.Dispose();
    }

    public static void Initialize(RuntimeContext context, Agent agent)
    {
        agent.Context = context;
        agent.Context.AgentInstance = agent;
        agent.Completion = agent.Start();
    }
}
