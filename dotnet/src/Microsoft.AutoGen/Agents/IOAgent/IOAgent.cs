// Copyright (c) Microsoft Corporation. All rights reserved.
// IOAgent.cs

using Microsoft.AutoGen.Contracts;
using Microsoft.AutoGen.Core;
namespace Microsoft.AutoGen.Agents;

public abstract class IOAgent(IAgentWorker worker, EventTypes eventTypes) : Agent(worker, eventTypes)
{
    public string _route = "base";

    public virtual async Task Handle(Input item)
    {

        var evt = new InputProcessed
        {
            Route = _route
        };
        await PublishMessageAsync(evt);
    }

    public virtual async Task Handle(Output item)
    {
        var evt = new OutputWritten
        {
            Route = _route
        };
        await PublishMessageAsync(evt);
    }

    public abstract Task ProcessInput(string message);
    public abstract Task ProcessOutput(string message);

}
