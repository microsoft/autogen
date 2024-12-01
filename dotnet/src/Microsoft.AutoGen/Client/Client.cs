// Copyright (c) Microsoft Corporation. All rights reserved.
// Client.cs

using System.Diagnostics;
using Microsoft.AutoGen.Abstractions;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;

namespace Microsoft.AutoGen.Core;

/// <summary>
/// Represents a client agent that interacts with the AutoGen system.
/// </summary>
/// <param name="runtime">The runtime environment for the agent worker.</param>
/// <param name="distributedContextPropagator">The context propagator for distributed tracing.</param>
/// <param name="eventTypes">The event types associated with the client.</param>
/// <param name="logger">The logger instance for logging client activities.</param>
public sealed class Client(IAgentWorker runtime, DistributedContextPropagator distributedContextPropagator,
    [FromKeyedServices("EventTypes")] EventTypes eventTypes, ILogger<Client> logger)
    : AgentBase(new RuntimeContext(new AgentId { Type = "client", Key = Guid.NewGuid().ToString() }, runtime, logger, distributedContextPropagator), eventTypes)
{
}
