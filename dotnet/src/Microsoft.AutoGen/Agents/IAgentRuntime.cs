// Copyright (c) Microsoft Corporation. All rights reserved.
// IAgentRuntime.cs

using System.Diagnostics;
using Microsoft.AutoGen.Abstractions;

namespace Microsoft.AutoGen.Agents;

public interface IAgentRuntime
{
    AgentId AgentId { get; }
    Agent? AgentInstance { get; set; }
    ValueTask StoreAsync(AgentState value, CancellationToken cancellationToken = default);
    ValueTask<AgentState> ReadAsync(AgentId agentId, CancellationToken cancellationToken = default);
    ValueTask SendResponseAsync(RpcRequest request, RpcResponse response, CancellationToken cancellationToken = default);
    ValueTask SendRequestAsync(Agent agent, RpcRequest request, CancellationToken cancellationToken = default);
    ValueTask SendMessageAsync(Message message, CancellationToken cancellationToken = default);
    ValueTask PublishEventAsync(CloudEvent @event, CancellationToken cancellationToken = default);
    void Update(RpcRequest request, Activity? activity);
    void Update(CloudEvent cloudEvent, Activity? activity);
    (string?, string?) GetTraceIdAndState(IDictionary<string, string> metadata);
    IDictionary<string, string> ExtractMetadata(IDictionary<string, string> metadata);
}
