// Copyright (c) Microsoft Corporation. All rights reserved.
// TestAgent.cs

using Microsoft.Extensions.Logging;
using Tests.Events;

namespace Microsoft.AutoGen.Core.Tests;

public class TestAgent(RuntimeContext context, EventTypes eventTypes, ILogger<AgentBase>? logger = null)
    : AgentBase(context, eventTypes, logger), IHandle<GoodBye>
{
    public Task Handle(GoodBye item, CancellationToken cancellationToken)
    {
        throw new NotImplementedException();
    }
}
