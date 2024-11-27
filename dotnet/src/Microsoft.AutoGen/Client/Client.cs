// Copyright (c) Microsoft Corporation. All rights reserved.
// Client.cs

using System.Diagnostics;
using Microsoft.AutoGen.Core;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;

namespace Microsoft.AutoGen.Client;
public sealed class Client(IAgentWorker runtime, DistributedContextPropagator distributedContextPropagator,
    [FromKeyedServices("EventTypes")] EventTypes eventTypes, ILogger<Client> logger)
    : AgentBase(new AgentRuntime(new AgentId { Type = "client", Key = Guid.NewGuid().ToString() }, runtime, logger, distributedContextPropagator), eventTypes)
{
}
