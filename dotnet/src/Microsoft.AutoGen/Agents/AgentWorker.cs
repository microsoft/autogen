// Copyright (c) Microsoft Corporation. All rights reserved.
// AgentWorker.cs

using System.Diagnostics;
using Google.Protobuf;
using Microsoft.AutoGen.Abstractions;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;

namespace Microsoft.AutoGen.Agents;
public sealed class AgentWorker(IAgentWorkerRuntime runtime, DistributedContextPropagator distributedContextPropagator,
    [FromKeyedServices("EventTypes")] EventTypes eventTypes, ILogger<AgentBase> logger)
    : AgentBase(new AgentContext(new AgentId("client", Guid.NewGuid().ToString()), runtime, logger, distributedContextPropagator), eventTypes)
{
    public async ValueTask PublishEventAsync(CloudEvent evt) => await base.PublishEventAsync(evt);

    public async ValueTask PublishEventAsync(string topic, IMessage evt)
    {
        await PublishEventAsync(evt.ToCloudEvent(topic)).ConfigureAwait(false);
    }
}
