// Copyright (c) Microsoft Corporation. All rights reserved.
// IAgentBase.cs

using Google.Protobuf;

namespace Microsoft.AutoGen.Abstractions;

public interface IAgentBase
{
    // Properties
    AgentId AgentId { get; }
    IAgentContext Context { get; }

    // Methods
    Task CallHandler(CloudEvent item);
    Task<RpcResponse> HandleRequest(RpcRequest request);
    void ReceiveMessage(Message message);
    Task Store(AgentState state);
    Task<T> Read<T>(AgentId agentId) where T : IMessage, new();
    ValueTask PublishEventAsync(CloudEvent item, CancellationToken token = default);
}
