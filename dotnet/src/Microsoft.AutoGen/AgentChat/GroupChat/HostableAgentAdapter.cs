// Copyright (c) Microsoft Corporation. All rights reserved.
// HostableAgentAdapter.cs

using Microsoft.AutoGen.Contracts;
using Microsoft.AutoGen.Core;
using Microsoft.Extensions.Logging;

namespace Microsoft.AutoGen.AgentChat.GroupChat;

public class AgentInstantiationContext(AgentId id, IAgentRuntime runtime)
{
    public AgentId Id { get; } = id;
    public IAgentRuntime Runtime { get; } = runtime;
}

internal class HostableAgentAdapter : BaseAgent
{
    public HostableAgentAdapter(AgentId id, IAgentRuntime runtime, string description, ILogger<BaseAgent>? logger = null) : base(id, runtime, description, logger)
    {
    }

    public HostableAgentAdapter(AgentInstantiationContext agentCtx, string description, ILogger<BaseAgent>? logger = null) : base(agentCtx.Id, agentCtx.Runtime, description, logger)
    {
    }
}

