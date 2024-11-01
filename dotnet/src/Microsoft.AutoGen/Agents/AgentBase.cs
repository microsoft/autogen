// Copyright (c) Microsoft Corporation. All rights reserved.
// AgentBase.cs

using System.Diagnostics;
using System.Reflection;
using System.Text;
using System.Text.Json;
using System.Threading.Channels;
using Google.Protobuf;
using Microsoft.AutoGen.Abstractions;
using Microsoft.Extensions.Logging;

namespace Microsoft.AutoGen.Agents;

public abstract class AgentBase : IAgentBase, IHandle
{
    public static readonly ActivitySource s_source = new("AutoGen.Agent");
    public AgentId AgentId => _context.AgentId;
    private readonly object _lock = new();
    private readonly Dictionary<string, TaskCompletionSource<RpcResponse>> _pendingRequests = [];

    private readonly Channel<object> _mailbox = Channel.CreateUnbounded<object>();
    private readonly IAgentContext _context;
    public string Route { get; set; } = "base";

    protected internal ILogger Logger => _context.Logger;
    public IAgentContext Context => _context;
    protected readonly EventTypes EventTypes;

    protected AgentBase(IAgentContext context, EventTypes eventTypes)
    {
        _context = context;
        context.AgentInstance = this;
        this.EventTypes = eventTypes;
        Completion = Start();
    }

    internal Task Completion { get; }

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
                        await HandleRpcMessage(msg).ConfigureAwait(false);
                        break;
                    default:
                        throw new InvalidOperationException($"Unexpected message '{message}'.");
                }
            }
            catch (Exception ex)
            {
                _context.Logger.LogError(ex, "Error processing message.");
            }
        }
    }

    protected internal async Task HandleRpcMessage(Message msg)
    {
        switch (msg.MessageCase)
        {
            case Message.MessageOneofCase.CloudEvent:
                {
                    var activity = this.ExtractActivity(msg.CloudEvent.Type, msg.CloudEvent.Metadata);
                    await this.InvokeWithActivityAsync(
                        static ((AgentBase Agent, CloudEvent Item) state) => state.Agent.CallHandler(state.Item),
                        (this, msg.CloudEvent),
                        activity,
                        msg.CloudEvent.Type).ConfigureAwait(false);
                }
                break;
            case Message.MessageOneofCase.Request:
                {
                    var activity = this.ExtractActivity(msg.Request.Method, msg.Request.Metadata);
                    await this.InvokeWithActivityAsync(
                        static ((AgentBase Agent, RpcRequest Request) state) => state.Agent.OnRequestCore(state.Request),
                        (this, msg.Request),
                        activity,
                        msg.Request.Method).ConfigureAwait(false);
                }
                break;
            case Message.MessageOneofCase.Response:
                OnResponseCore(msg.Response);
                break;
        }
    }
    public async Task Store(AgentState state)
    {
        await _context.Store(state).ConfigureAwait(false);
        return;
    }
    public async Task<T> Read<T>(AgentId agentId) where T : IMessage, new()
    {
        var agentstate = await _context.Read(agentId).ConfigureAwait(false);
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
    private async Task OnRequestCore(RpcRequest request)
    {
        RpcResponse response;

        try
        {
            response = await HandleRequest(request).ConfigureAwait(false);
        }
        catch (Exception ex)
        {
            response = new RpcResponse { Error = ex.Message };
        }

        await _context.SendResponseAsync(request, response).ConfigureAwait(false);
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
        Context.DistributedContextPropagator.Inject(activity, request.Metadata, static (carrier, key, value) => ((IDictionary<string, string>)carrier!)[key] = value);
        await this.InvokeWithActivityAsync(
            static async ((AgentBase Agent, RpcRequest Request, TaskCompletionSource<RpcResponse>) state) =>
            {
                var (self, request, completion) = state;

                lock (self._lock)
                {
                    self._pendingRequests[request.RequestId] = completion;
                }

                await state.Agent._context.SendRequestAsync(state.Agent, state.Request).ConfigureAwait(false);

                await completion.Task.ConfigureAwait(false);
            },
            (this, request, completion),
            activity,
            method).ConfigureAwait(false);

        // Return the result from the already-completed task
        return await completion.Task.ConfigureAwait(false);
    }

    public async ValueTask PublishEvent(CloudEvent item)
    {
        var activity = s_source.StartActivity($"PublishEvent '{item.Type}'", ActivityKind.Client, Activity.Current?.Context ?? default);
        activity?.SetTag("peer.service", $"{item.Type}/{item.Source}");

        // TODO: fix activity
        Context.DistributedContextPropagator.Inject(activity, item.Metadata, static (carrier, key, value) => ((IDictionary<string, string>)carrier!)[key] = value);
        await this.InvokeWithActivityAsync(
            static async ((AgentBase Agent, CloudEvent Event) state) =>
            {
                await state.Agent._context.PublishEventAsync(state.Event).ConfigureAwait(false);
            },
            (this, item),
            activity,
            item.Type).ConfigureAwait(false);
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
                    Logger.LogError(ex, $"Error invoking method {nameof(IHandle<object>.Handle)}");
                    throw; // TODO: ?
                }
            }
        }

        return Task.CompletedTask;
    }

    public Task<RpcResponse> HandleRequest(RpcRequest request) => Task.FromResult(new RpcResponse { Error = "Not implemented" });

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
}
