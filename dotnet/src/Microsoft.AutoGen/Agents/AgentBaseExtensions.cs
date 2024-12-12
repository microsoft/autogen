// Copyright (c) Microsoft Corporation. All rights reserved.
// AgentExtensions.cs

using System.Diagnostics;
using Google.Protobuf.Collections;
using static Microsoft.AutoGen.Abstractions.CloudEvent.Types;

namespace Microsoft.AutoGen.Agents;

/// <summary>
/// Provides extension methods for the <see cref="Agent"/> class.
/// </summary>
public static class AgentExtensions
{
    /// <summary>
    /// Extracts an <see cref="Activity"/> from the given agent and metadata.
    /// </summary>
    /// <param name="agent">The agent from which to extract the activity.</param>
    /// <param name="activityName">The name of the activity.</param>
    /// <param name="metadata">The metadata containing trace information.</param>
    /// <returns>The extracted <see cref="Activity"/> or null if extraction fails.</returns>
    public static Activity? ExtractActivity(this Agent agent, string activityName, IDictionary<string, string> metadata)
    {
        Activity? activity;
        var (traceParent, traceState) = agent.Context.GetTraceIdAndState(metadata);
        if (!string.IsNullOrEmpty(traceParent))
        {
            if (ActivityContext.TryParse(traceParent, traceState, isRemote: true, out var parentContext))
            {
                // traceParent is a W3CId
                activity = Agent.s_source.CreateActivity(activityName, ActivityKind.Server, parentContext);
            }
            else
            {
                // Most likely, traceParent uses ActivityIdFormat.Hierarchical
                activity = Agent.s_source.CreateActivity(activityName, ActivityKind.Server, traceParent);
            }

            if (activity is not null)
            {
                if (!string.IsNullOrEmpty(traceState))
                {
                    activity.TraceStateString = traceState;
                }

                var baggage = agent.Context.ExtractMetadata(metadata);

                foreach (var baggageItem in baggage)
                {
                    activity.AddBaggage(baggageItem.Key, baggageItem.Value);
                }
            }
        }
        else
        {
            activity = Agent.s_source.CreateActivity(activityName, ActivityKind.Server);
        }

        return activity;
    }

    public static Activity? ExtractActivity(this Agent agent, string activityName, MapField<string, CloudEventAttributeValue> metadata)
    {
        return ExtractActivity(agent, activityName, metadata.ToDictionary(kvp => kvp.Key, kvp => kvp.Value.CeString));
    }

    /// <summary>
    /// Invokes a function asynchronously within the context of an <see cref="Activity"/>.
    /// </summary>
    /// <typeparam name="TState">The type of the state parameter.</typeparam>
    /// <param name="agent">The agent invoking the function.</param>
    /// <param name="func">The function to invoke.</param>
    /// <param name="state">The state parameter to pass to the function.</param>
    /// <param name="activity">The activity within which to invoke the function.</param>
    /// <param name="methodName">The name of the method being invoked.</param>
    /// <param name="cancellationToken">A token to monitor for cancellation requests.</param>
    /// <returns>A task representing the asynchronous operation.</returns>
    public static async Task InvokeWithActivityAsync<TState>(this Agent agent, Func<TState, CancellationToken, Task> func, TState state, Activity? activity, string methodName, CancellationToken cancellationToken = default)
    {
        if (activity is not null && activity.StartTimeUtc == default)
        {
            activity.Start();

            // rpc attributes from https://github.com/open-telemetry/opentelemetry-specification/blob/main/specification/trace/semantic_conventions/rpc.md
            activity.SetTag("rpc.system", "autogen");
            activity.SetTag("rpc.service", agent.AgentId.ToString());
            activity.SetTag("rpc.method", methodName);
        }

        try
        {
            await func(state, cancellationToken).ConfigureAwait(false);
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
