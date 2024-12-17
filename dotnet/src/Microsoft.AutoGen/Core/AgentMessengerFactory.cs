// Copyright (c) Microsoft Corporation. All rights reserved.
// AgentMessengerFactory.cs

using System.Diagnostics;
namespace Microsoft.AutoGen.Core;
public class AgentMessengerFactory()
{
    public static AgentMessenger Create(IAgentWorker worker, DistributedContextPropagator distributedContextPropagator)
    {
        return new AgentMessenger(worker, distributedContextPropagator);
    }
}
