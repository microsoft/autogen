// Copyright (c) Microsoft Corporation. All rights reserved.
// RuntimeContext.cs

using System.Diagnostics;
using Google.Protobuf.Collections;
using Microsoft.AutoGen.Contracts;
using Microsoft.Extensions.Logging;
using static Microsoft.AutoGen.Contracts.CloudEvent.Types;

namespace Microsoft.AutoGen.Core;

/// <summary>
/// Represents the runtime environment for an agent.
/// </summary>
/// <param name="agentId">The unique identifier of the agent.</param>
/// <param name="worker">The worker responsible for agent operations.</param>
/// <param name="logger">The logger instance for logging.</param>
/// <param name="distributedContextPropagator">The context propagator for distributed tracing.</param>
public sealed class RuntimeContext(AgentId agentId, IAgentWorker worker, ILogger<Agent> logger, DistributedContextPropagator distributedContextPropagator)
{
    private readonly IAgentWorker worker = worker;

    /// <summary>
    /// Gets the unique identifier of the agent.
    /// </summary>
    public AgentId AgentId { get; } = agentId;

    /// <summary>
    /// Gets the logger instance for logging.
    /// </summary>
    public ILogger<Agent> Logger { get; } = logger;

    /// <summary>
    /// Gets or sets the instance of the agent.
    /// </summary>
    public Agent? AgentInstance { get; internal set; }

    /// <summary>
    /// Gets the context propagator for distributed tracing.
    /// </summary>
    private DistributedContextPropagator DistributedContextPropagator { get; } = distributedContextPropagator;

    /// <summary>
    /// Extracts the trace ID and state from the given metadata.
    /// </summary>
    /// <param name="metadata">The metadata containing trace information.</param>
    /// <returns>A tuple containing the trace ID and state.</returns>
    public (string?, string?) GetTraceIdAndState(IDictionary<string, string> metadata)
    {
        DistributedContextPropagator.ExtractTraceIdAndState(metadata,
            static (object? carrier, string fieldName, out string? fieldValue, out IEnumerable<string>? fieldValues) =>
            {
                var metadata = (IDictionary<string, string>)carrier!;
                fieldValues = null;
                metadata.TryGetValue(fieldName, out fieldValue);
            },
            out var traceParent,
            out var traceState);
        return (traceParent, traceState);
    }

    /// <summary>
    /// Updates the dcp with metadata from the current request
    /// </summary>
    /// <param name="request">The request to update.</param>
    /// <param name="activity">The current activity context.</param>
    public void Update(RpcRequest request, Activity? activity = null)
    {
        DistributedContextPropagator.Inject(activity, request.Metadata, static (carrier, key, value) =>
        {
            var metadata = (IDictionary<string, string>)carrier!;
            if (metadata.TryGetValue(key, out _))
            {
                metadata[key] = value;
            }
            else
            {
                metadata.Add(key, value);
            }
        });
    }
    /// <summary>
    /// Updates the dcp with metadata from the current cloud event
    /// </summary>
    /// <param name="cloudEvent">The request to update.</param>
    /// <param name="activity">The current activity context.</param>
    public void Update(CloudEvent cloudEvent, Activity? activity = null)
    {
        DistributedContextPropagator.Inject(activity, cloudEvent.Attributes, static (carrier, key, value) =>
        {
            var mapField = (MapField<string, CloudEventAttributeValue>)carrier!;
            if (mapField.TryGetValue(key, out var ceValue))
            {
                mapField[key] = new CloudEventAttributeValue { CeString = value };
            }
            else
            {
                mapField.Add(key, new CloudEventAttributeValue { CeString = value });
            }
        });
    }

    /// <summary>
    /// Sends a response asynchronously.
    /// </summary>
    /// <param name="request">The request associated with the response.</param>
    /// <param name="response">The response to send.</param>
    /// <param name="cancellationToken">A token to cancel the operation.</param>
    /// <returns>A task that represents the asynchronous operation.</returns>
    public async ValueTask SendResponseAsync(RpcRequest request, RpcResponse response, CancellationToken cancellationToken = default)
    {
        response.RequestId = request.RequestId;
        await worker.SendResponseAsync(response, cancellationToken).ConfigureAwait(false);
    }

    /// <summary>
    /// Sends a request asynchronously.
    /// </summary>
    /// <param name="agent">The agent sending the request.</param>
    /// <param name="request">The request to send.</param>
    /// <param name="cancellationToken">A token to cancel the operation.</param>
    /// <returns>A task that represents the asynchronous operation.</returns>
    public async ValueTask SendRequestAsync(Agent agent, RpcRequest request, CancellationToken cancellationToken = default)
    {
        await worker.SendRequestAsync(agent, request, cancellationToken).ConfigureAwait(false);
    }

    /// <summary>
    /// Sends a message asynchronously.
    /// </summary>
    /// <param name="message">The message to send.</param>
    /// <param name="cancellationToken">A token to cancel the operation.</param>
    /// <returns>A task that represents the asynchronous operation.</returns>
    public async ValueTask SendMessageAsync(Message message, CancellationToken cancellationToken = default)
    {
        await worker.SendMessageAsync(message, cancellationToken).ConfigureAwait(false);
    }

    /// <summary>
    /// Publishes a cloud event asynchronously.
    /// </summary>
    /// <param name="event">The cloud event to publish.</param>
    /// <param name="cancellationToken">A token to cancel the operation.</param>
    /// <returns>A task that represents the asynchronous operation.</returns>
    public async ValueTask PublishEventAsync(CloudEvent @event, CancellationToken cancellationToken = default)
    {
        await worker.PublishEventAsync(@event, cancellationToken).ConfigureAwait(false);
    }

    /// <summary>
    /// Stores the agent state asynchronously.
    /// </summary>
    /// <param name="value">The agent state to store.</param>
    /// <param name="cancellationToken">A token to cancel the operation.</param>
    /// <returns>A task that represents the asynchronous operation.</returns>
    public async ValueTask StoreAsync(AgentState value, CancellationToken cancellationToken = default)
    {
        await worker.StoreAsync(value, cancellationToken).ConfigureAwait(false);
    }

    /// <summary>
    /// Reads the agent state asynchronously.
    /// </summary>
    /// <param name="agentId">The ID of the agent whose state is to be read.</param>
    /// <param name="cancellationToken">A token to cancel the operation.</param>
    /// <returns>A task that represents the asynchronous operation, containing the agent state.</returns>
    public ValueTask<AgentState> ReadAsync(AgentId agentId, CancellationToken cancellationToken = default)
    {
        return worker.ReadAsync(agentId, cancellationToken);
    }

    /// <summary>
    /// Extracts metadata from the given metadata dictionary.
    /// </summary>
    /// <param name="metadata">The metadata dictionary to extract from.</param>
    /// <returns>A dictionary containing the extracted metadata.</returns>
    public IDictionary<string, string> ExtractMetadata(IDictionary<string, string> metadata)
    {
        var baggage = DistributedContextPropagator.ExtractBaggage(metadata, static (object? carrier, string fieldName, out string? fieldValue, out IEnumerable<string>? fieldValues) =>
        {
            var metadata = (IDictionary<string, string>)carrier!;
            fieldValues = null;
            metadata.TryGetValue(fieldName, out fieldValue);
        });

        return baggage as IDictionary<string, string> ?? new Dictionary<string, string>();
    }
}
