// Copyright (c) Microsoft Corporation. All rights reserved.
// Client.cs
using Microsoft.Extensions.DependencyInjection;

namespace Microsoft.AutoGen.Core;
public sealed class Client(IAgentWorker worker, [FromKeyedServices("EventTypes")] EventTypes eventTypes)
    : Agent(worker, eventTypes)
{
}
