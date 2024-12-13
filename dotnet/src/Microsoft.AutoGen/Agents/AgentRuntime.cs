// Copyright (c) Microsoft Corporation. All rights reserved.
// AgentRuntime.cs

using System.Diagnostics;
using Google.Protobuf.Collections;
using Microsoft.AutoGen.Contracts;
using Microsoft.Extensions.Logging;
using static Microsoft.AutoGen.Contracts.CloudEvent.Types;

namespace Microsoft.AutoGen.Agents;

public sealed class AgentRuntime(AgentId agentId, IAgentWorker worker, ILogger<Agent> logger, DistributedContextPropagator distributedContextPropagator) : IAgentRuntime
{
    private readonly IAgentWorker worker = worker;

    public AgentId AgentId { get; } = agentId;
    private ILogger<Agent> Logger { get; } = logger;
    public Agent? AgentInstance { get; set; }
    private DistributedContextPropagator DistributedContextPropagator { get; } = distributedContextPropagator;
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
    public (string?, string?) GetTraceIdAndState(MapField<string, CloudEventAttributeValue> metadata)
    {
        DistributedContextPropagator.ExtractTraceIdAndState(metadata,
            static (object? carrier, string fieldName, out string? fieldValue, out IEnumerable<string>? fieldValues) =>
            {
                var metadata = (MapField<string, CloudEventAttributeValue>)carrier!;
                fieldValues = null;
                metadata.TryGetValue(fieldName, out var ceValue);
                fieldValue = ceValue?.CeString;
            },
            out var traceParent,
            out var traceState);
        return (traceParent, traceState);
    }
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
    public async ValueTask SendResponseAsync(RpcRequest request, RpcResponse response, CancellationToken cancellationToken = default)
    {
        response.RequestId = request.RequestId;
        await worker.SendResponseAsync(response, cancellationToken).ConfigureAwait(false);
    }
    public async ValueTask SendRequestAsync(Agent agent, RpcRequest request, CancellationToken cancellationToken = default)
    {
        await worker.SendRequestAsync(agent, request, cancellationToken).ConfigureAwait(false);
    }
    public async ValueTask SendMessageAsync(Message message, CancellationToken cancellationToken = default)
    {
        await worker.SendMessageAsync(message, cancellationToken).ConfigureAwait(false);
    }
    public async ValueTask PublishEventAsync(CloudEvent @event, CancellationToken cancellationToken = default)
    {
        await worker.PublishEventAsync(@event, cancellationToken).ConfigureAwait(false);
    }
    public async ValueTask StoreAsync(AgentState value, CancellationToken cancellationToken = default)
    {
        await worker.StoreAsync(value, cancellationToken).ConfigureAwait(false);
    }
    public ValueTask<AgentState> ReadAsync(AgentId agentId, CancellationToken cancellationToken = default)
    {
        return worker.ReadAsync(agentId, cancellationToken);
    }

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

    public IDictionary<string, string> ExtractMetadata(MapField<string, CloudEventAttributeValue> metadata)
    {
        var baggage = DistributedContextPropagator.ExtractBaggage(metadata, static (object? carrier, string fieldName, out string? fieldValue, out IEnumerable<string>? fieldValues) =>
        {
            var metadata = (MapField<string, CloudEventAttributeValue>)carrier!;
            fieldValues = null;
            metadata.TryGetValue(fieldName, out var ceValue);
            fieldValue = ceValue?.CeString;
        });

        return baggage as IDictionary<string, string> ?? new Dictionary<string, string>();
    }
}
