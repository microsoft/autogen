using Agents;
using System.Threading.Channels;
using Microsoft.Extensions.Logging;
using System.Text.Json;
using System.Diagnostics;

namespace Microsoft.AI.Agents.Worker.Client;

public abstract class AgentBase
{
    private static readonly ActivitySource s_source = new("Starfleet.Agent");
    private readonly object _lock = new();
    private readonly Dictionary<string, TaskCompletionSource<RpcResponse>> _pendingRequests = [];
    private readonly Channel<object> _mailbox = Channel.CreateUnbounded<object>();
    private readonly IAgentContext _context;

    protected internal AgentId AgentId => _context.AgentId;
    protected internal ILogger Logger => _context.Logger;
    protected internal IAgentContext Context => _context;

    protected AgentBase(IAgentContext context)
    {
        _context = context;
        context.AgentInstance = this;
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
            case Message.MessageOneofCase.Event:
                {
                    var activity = ExtractActivity(msg.Event.Type, msg.Event.Metadata);
                    await InvokeWithActivityAsync(
                        static ((AgentBase Agent, Event Item) state) => state.Agent.HandleEvent(state.Item),
                        (this, msg.Event),
                        activity,
                        msg.Event.Type).ConfigureAwait(false);
                }
                break;
            case Message.MessageOneofCase.Request:
                {
                    var activity = ExtractActivity(msg.Request.Method, msg.Request.Metadata);
                    await InvokeWithActivityAsync(
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
            Data = JsonSerializer.Serialize(parameters)
        };

        var activity = s_source.StartActivity($"Call '{method}'", ActivityKind.Client, Activity.Current?.Context ?? default);
        activity?.SetTag("peer.service", target.ToString());

        var completion = new TaskCompletionSource<RpcResponse>(TaskCreationOptions.RunContinuationsAsynchronously);
        Context.DistributedContextPropagator.Inject(activity, request.Metadata, static (carrier, key, value) => ((IDictionary<string, string>)carrier!)[key] = value);
        await InvokeWithActivityAsync(
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

    protected async ValueTask PublishEvent(Event item)
    {
        var activity = s_source.StartActivity($"PublishEvent '{item.Type}'", ActivityKind.Client, Activity.Current?.Context ?? default);
        activity?.SetTag("peer.service", $"{item.Type}/{item.Namespace}");

        var completion = new TaskCompletionSource<RpcResponse>(TaskCreationOptions.RunContinuationsAsynchronously);
        Context.DistributedContextPropagator.Inject(activity, item.Metadata, static (carrier, key, value) => ((IDictionary<string, string>)carrier!)[key] = value);
        await InvokeWithActivityAsync(
            static async ((AgentBase Agent, Event Event, TaskCompletionSource<RpcResponse>) state) =>
            {
                await state.Agent._context.PublishEventAsync(state.Event).ConfigureAwait(false);
            },
            (this, item, completion),
            activity,
            item.Type).ConfigureAwait(false);
    }

    protected virtual Task<RpcResponse> HandleRequest(RpcRequest request) => Task.FromResult(new RpcResponse { Error = "Not implemented" });

    protected virtual Task HandleEvent(Event item) => Task.CompletedTask;

    protected async Task InvokeWithActivityAsync<TState>(Func<TState, Task> func, TState state, Activity? activity, string methodName)
    {
        if (activity is not null)
        {
            activity.Start();

            // rpc attributes from https://github.com/open-telemetry/opentelemetry-specification/blob/main/specification/trace/semantic_conventions/rpc.md
            activity.SetTag("rpc.system", "starfleet");
            activity.SetTag("rpc.service", AgentId.ToString());
            activity.SetTag("rpc.method", methodName);
        }

        try
        {
            await func(state).ConfigureAwait(false);
            if (activity is not null && activity.IsAllDataRequested)
            {
                activity.SetStatus(ActivityStatusCode.Ok);
            }
        }
        catch (Exception e)
        {
            if (activity is not null && activity.IsAllDataRequested)
            {
                activity.SetStatus(ActivityStatusCode.Error);

                // exception attributes from https://github.com/open-telemetry/opentelemetry-specification/blob/main/specification/trace/semantic_conventions/exceptions.md
                activity.SetTag("exception.type", e.GetType().FullName);
                activity.SetTag("exception.message", e.Message);

                // Note that "exception.stacktrace" is the full exception detail, not just the StackTrace property. 
                // See https://opentelemetry.io/docs/specs/semconv/attributes-registry/exception/
                // and https://github.com/open-telemetry/opentelemetry-specification/pull/697#discussion_r453662519
                activity.SetTag("exception.stacktrace", e.ToString());
                activity.SetTag("exception.escaped", true);
            }

            throw;
        }
        finally
        {
            activity?.Stop();
        }
    }

    private Activity? ExtractActivity(string activityName, IDictionary<string, string> metadata)
    {
        Activity? activity = null;
        Context.DistributedContextPropagator.ExtractTraceIdAndState(metadata,
            static (object? carrier, string fieldName, out string? fieldValue, out IEnumerable<string>? fieldValues) =>
            {
                var metadata = (IDictionary<string, string>)carrier!;
                fieldValues = null;
                metadata.TryGetValue(fieldName, out fieldValue);
            },
            out var traceParent,
            out var traceState);

        if (!string.IsNullOrEmpty(traceParent))
        {
            if (ActivityContext.TryParse(traceParent, traceState, isRemote: true, out ActivityContext parentContext))
            {
                // traceParent is a W3CId
                activity = s_source.CreateActivity(activityName, ActivityKind.Server, parentContext);
            }
            else
            {
                // Most likely, traceParent uses ActivityIdFormat.Hierarchical
                activity = s_source.CreateActivity(activityName, ActivityKind.Server, traceParent);
            }

            if (activity is not null)
            {
                if (!string.IsNullOrEmpty(traceState))
                {
                    activity.TraceStateString = traceState;
                }

                var baggage = Context.DistributedContextPropagator.ExtractBaggage(metadata, static (object? carrier, string fieldName, out string? fieldValue, out IEnumerable<string>? fieldValues) =>
                {
                    var metadata = (IDictionary<string, string>)carrier!;
                    fieldValues = null;
                    metadata.TryGetValue(fieldName, out fieldValue);
                });

                if (baggage is not null)
                {
                    foreach (var baggageItem in baggage)
                    {
                        activity.AddBaggage(baggageItem.Key, baggageItem.Value);
                    }
                }
            }
        }
        else
        {
            activity = s_source.CreateActivity(activityName, ActivityKind.Server);
        }

        return activity;
    }
}
