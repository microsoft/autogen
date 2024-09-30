using System.Diagnostics;

namespace Microsoft.AutoGen.Agents.Client;

public static class AgentBaseExtensions
{
   

    public static Activity? ExtractActivity(this AgentBase agent, string activityName, IDictionary<string, string> metadata)
    {
        Activity? activity = null;
        agent.Context.DistributedContextPropagator.ExtractTraceIdAndState(metadata,
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
                activity = AgentBase.s_source.CreateActivity(activityName, ActivityKind.Server, parentContext);
            }
            else
            {
                // Most likely, traceParent uses ActivityIdFormat.Hierarchical
                activity = AgentBase.s_source.CreateActivity(activityName, ActivityKind.Server, traceParent);
            }

            if (activity is not null)
            {
                if (!string.IsNullOrEmpty(traceState))
                {
                    activity.TraceStateString = traceState;
                }

                var baggage = agent.Context.DistributedContextPropagator.ExtractBaggage(metadata, static (object? carrier, string fieldName, out string? fieldValue, out IEnumerable<string>? fieldValues) =>
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
            activity = AgentBase.s_source.CreateActivity(activityName, ActivityKind.Server);
        }

        return activity;
    }

    public static async Task InvokeWithActivityAsync<TState>(this AgentBase agent, Func<TState, Task> func, TState state, Activity? activity, string methodName)
    {
        if (activity is not null)
        {
            activity.Start();

            // rpc attributes from https://github.com/open-telemetry/opentelemetry-specification/blob/main/specification/trace/semantic_conventions/rpc.md
            activity.SetTag("rpc.system", "autogen");
            activity.SetTag("rpc.service", agent.AgentId.ToString());
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
}
