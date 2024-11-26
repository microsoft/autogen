// Copyright (c) Microsoft Corporation. All rights reserved.
// AgentRuntime.cs

using System.Diagnostics;
using Microsoft.AutoGen.Abstractions;
using Microsoft.Extensions.Logging;

namespace Microsoft.AutoGen.Agents;

internal sealed class AgentRuntime(AgentId agentId, IAgentWorker worker, ILogger<AgentBase> logger, DistributedContextPropagator distributedContextPropagator) : IAgentRuntime
{
    private readonly IAgentWorker worker = worker;

    public AgentId AgentId { get; } = agentId;
    public ILogger<AgentBase> Logger { get; } = logger;
    public IAgentBase? AgentInstance { get; set; }
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
    public void Update(RpcRequest request, Activity? activity = null)
    {
        DistributedContextPropagator.Inject(activity, request.Metadata, static (carrier, key, value) => ((IDictionary<string, string>)carrier!)[key] = value);
    }
    public void Update(CloudEvent cloudEvent, Activity? activity = null)
    {
        DistributedContextPropagator.Inject(activity, cloudEvent.Metadata, static (carrier, key, value) => ((IDictionary<string, string>)carrier!)[key] = value);
    }
    public async ValueTask SendResponseAsync(RpcRequest request, RpcResponse response, CancellationToken cancellationToken = default)
    {
        response.RequestId = request.RequestId;
        await worker.SendResponseAsync(response, cancellationToken).ConfigureAwait(false);
    }
    public async ValueTask SendRequestAsync(IAgentBase agent, RpcRequest request, CancellationToken cancellationToken = default)
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
}
