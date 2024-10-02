using System.Diagnostics;
using System.Text;
using System.Text.Json;
using System.Threading.Channels;
using Google.Protobuf;
using Microsoft.AutoGen.Agents.Abstractions;
using Microsoft.Extensions.Logging;

namespace Microsoft.AutoGen.Agents.Client;

public abstract class AgentBase
{
    public static readonly ActivitySource s_source = new("AutoGen.Agent");
    private readonly object _lock = new();
    private readonly Dictionary<string, TaskCompletionSource<RpcResponse>> _pendingRequests = [];

    private readonly Channel<object> _mailbox = Channel.CreateUnbounded<object>();
    private readonly IAgentContext _context;

    protected internal AgentId AgentId => _context.AgentId;
    protected internal ILogger Logger => _context.Logger;
    protected internal IAgentContext Context => _context;
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

    internal void ReceiveMessage(Message message) => _mailbox.Writer.TryWrite(message);

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

    private async Task HandleRpcMessage(Message msg)
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

    protected async ValueTask PublishEvent(CloudEvent item)
    {
        //TODO: Reimplement
        var activity = s_source.StartActivity($"PublishEvent '{item.Type}'", ActivityKind.Client, Activity.Current?.Context ?? default);
        activity?.SetTag("peer.service", $"{item.Type}/{item.Source}");

        var completion = new TaskCompletionSource<CloudEvent>(TaskCreationOptions.RunContinuationsAsynchronously);
        // TODO: fix activity
        Context.DistributedContextPropagator.Inject(activity, item.Metadata, static (carrier, key, value) => ((IDictionary<string, string>)carrier!)[key] = value);
        await this.InvokeWithActivityAsync(
            static async ((AgentBase Agent, CloudEvent Event, TaskCompletionSource<CloudEvent>) state) =>
            {
                await state.Agent._context.PublishEventAsync(state.Event).ConfigureAwait(false);
            },
            (this, item, completion),
            activity,
            item.Type).ConfigureAwait(false);// TODO: It's not the descriptor's name probably
    }

    public Task CallHandler(CloudEvent item)
    {
        // Only send the event to the handler if the agent type is handling that type
        if (EventTypes.EventsMap[GetType()].Contains(item.Type))
        {
            var payload = item.ProtoData.Unpack(EventTypes.TypeRegistry);
            var convertedPayload = Convert.ChangeType(payload, EventTypes.Types[item.Type]);
            var genericInterfaceType = typeof(IHandle<>).MakeGenericType(EventTypes.Types[item.Type]);
            var methodInfo = genericInterfaceType.GetMethod(nameof(IHandle<object>.Handle)) ?? throw new InvalidOperationException($"Method not found on type {genericInterfaceType.FullName}");
            return methodInfo.Invoke(this, [payload]) as Task ?? Task.CompletedTask;
        }
        return Task.CompletedTask;
    }

    protected virtual Task<RpcResponse> HandleRequest(RpcRequest request) => Task.FromResult(new RpcResponse { Error = "Not implemented" });
}
