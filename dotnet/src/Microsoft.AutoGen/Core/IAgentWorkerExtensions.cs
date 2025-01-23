// Copyright (c) Microsoft Corporation. All rights reserved.
// IAgentWorkerExtensions.cs

using System.Diagnostics;
using Google.Protobuf.Collections;
using Microsoft.AutoGen.Contracts;
using Microsoft.Extensions.DependencyInjection;
using static Microsoft.AutoGen.Contracts.CloudEvent.Types;

namespace Microsoft.AutoGen.Core;

public static class IAgentWorkerExtensions
{
    public static (string?, string?) GetTraceIdAndState(IAgentWorker worker, IDictionary<string, string> metadata)
    {
        var dcp = worker.ServiceProvider.GetRequiredService<DistributedContextPropagator>();
        dcp.ExtractTraceIdAndState(metadata,
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
    public static (string?, string?) GetTraceIdAndState(IAgentWorker worker, MapField<string, CloudEventAttributeValue> metadata)
    {
        var dcp = worker.ServiceProvider.GetRequiredService<DistributedContextPropagator>();
        dcp.ExtractTraceIdAndState(metadata,
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
    public static void Update(IAgentWorker worker, RpcRequest request, Activity? activity = null)
    {
        var dcp = worker.ServiceProvider.GetRequiredService<DistributedContextPropagator>();
        dcp.Inject(activity, request.Metadata, static (carrier, key, value) =>
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
    public static void Update(IAgentWorker worker, CloudEvent cloudEvent, Activity? activity = null)
    {
        var dcp = worker.ServiceProvider.GetRequiredService<DistributedContextPropagator>();
        dcp.Inject(activity, cloudEvent.Attributes, static (carrier, key, value) =>
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

    public static IDictionary<string, string> ExtractMetadata(IAgentWorker worker, IDictionary<string, string> metadata)
    {
        var dcp = worker.ServiceProvider.GetRequiredService<DistributedContextPropagator>();
        var baggage = dcp.ExtractBaggage(metadata, static (object? carrier, string fieldName, out string? fieldValue, out IEnumerable<string>? fieldValues) =>
        {
            var metadata = (IDictionary<string, string>)carrier!;
            fieldValues = null;
            metadata.TryGetValue(fieldName, out fieldValue);
        });

        return baggage as IDictionary<string, string> ?? new Dictionary<string, string>();
    }
    public static IDictionary<string, string> ExtractMetadata(IAgentWorker worker, MapField<string, CloudEventAttributeValue> metadata)
    {
        var dcp = worker.ServiceProvider.GetRequiredService<DistributedContextPropagator>();
        var baggage = dcp.ExtractBaggage(metadata, static (object? carrier, string fieldName, out string? fieldValue, out IEnumerable<string>? fieldValues) =>
        {
            var metadata = (MapField<string, CloudEventAttributeValue>)carrier!;
            fieldValues = null;
            metadata.TryGetValue(fieldName, out var ceValue);
            fieldValue = ceValue?.CeString;
        });

        return baggage as IDictionary<string, string> ?? new Dictionary<string, string>();
    }
}
