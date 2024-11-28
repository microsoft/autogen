// Copyright (c) Microsoft Corporation. All rights reserved.
// AgentClient.cs

using System.Diagnostics;
using Microsoft.AutoGen.Abstractions;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;

namespace Microsoft.AutoGen.Client;
public sealed class AgentClient(IAgentWorker runtime, DistributedContextPropagator distributedContextPropagator,
    [FromKeyedServices("EventTypes")] EventTypes eventTypes, ILogger<AgentClient> logger)
    : AgentBase(new AgentRuntime(new AgentId { Type = "client", Key = Guid.NewGuid().ToString() }, runtime, logger, distributedContextPropagator), eventTypes)
{
}
