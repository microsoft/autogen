// Copyright (c) Microsoft Corporation. All rights reserved.
// IAgentWorker.cs

namespace Microsoft.AutoGen.Abstractions;

public interface IAgentWorker
{
    ValueTask PublishEventAsync(CloudEvent evt, CancellationToken cancellationToken = default);
    ValueTask SendRequestAsync(IAgentBase agent, RpcRequest request, CancellationToken cancellationToken = default);
    ValueTask SendResponseAsync(RpcResponse response, CancellationToken cancellationToken = default);
    ValueTask StoreAsync(AgentState value, CancellationToken cancellationToken = default);
    ValueTask<AgentState> ReadAsync(AgentId agentId, CancellationToken cancellationToken = default);
}
