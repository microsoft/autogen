// Copyright (c) Microsoft Corporation. All rights reserved.
// AgentMessengerFactory.cs

using System.Diagnostics;
using Microsoft.AutoGen.Contracts;
using Microsoft.Extensions.Logging;

namespace Microsoft.AutoGen.Core;
public class AgentMessengerFactory()
{
    public static AgentMessenger Create(AgentId agentId, IAgentWorker worker, ILogger<Agent> logger, DistributedContextPropagator distributedContextPropagator)
    {
        return new AgentMessenger(agentId, worker, logger, distributedContextPropagator);
    }
}