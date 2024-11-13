// Copyright (c) Microsoft Corporation. All rights reserved.
// IAgentRuntime.cs

using System.Diagnostics;

namespace Microsoft.AutoGen.Abstractions;

public interface IAgentRuntime
{
    AgentId AgentId { get; }
    IAgentBase? AgentInstance { get; set; }
    ValueTask StoreAsync(AgentState value, CancellationToken cancellationToken = default);
    ValueTask<AgentState> ReadAsync(AgentId agentId, CancellationToken cancellationToken = default);
    ValueTask SendResponseAsync(RpcRequest request, RpcResponse response, CancellationToken cancellationToken = default);
    ValueTask SendRequestAsync(IAgentBase agent, RpcRequest request, CancellationToken cancellationToken = default);
    ValueTask PublishEventAsync(CloudEvent @event, CancellationToken cancellationToken = default);
    void Update(Activity? activity, RpcRequest request);
    void Update(Activity? activity, CloudEvent cloudEvent);
    (string?, string?) GetTraceIDandState(IDictionary<string, string> metadata);
    IDictionary<string, string> ExtractMetadata(IDictionary<string, string> metadata);
}
