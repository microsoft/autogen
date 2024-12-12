// Copyright (c) Microsoft Corporation. All rights reserved.
// Client.cs

using System.Diagnostics;
using Microsoft.AutoGen.Abstractions;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;

namespace Microsoft.AutoGen.Agents;
public sealed class Client(IAgentWorker runtime, DistributedContextPropagator distributedContextPropagator,
    [FromKeyedServices("EventTypes")] EventTypes eventTypes, ILogger<Client> logger)
    : Agent(new AgentRuntime(new AgentId("client", Guid.NewGuid().ToString()), runtime, logger, distributedContextPropagator), eventTypes)
{
}
