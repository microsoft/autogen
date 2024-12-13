// Copyright (c) Microsoft Corporation. All rights reserved.
// ConsoleAgent.cs

using Microsoft.AutoGen.Contracts;
using Microsoft.Extensions.DependencyInjection;

namespace Microsoft.AutoGen.Agents;

public abstract class ConsoleAgent : IOAgent,
        IUseConsole,
        IHandle<Input>,
        IHandle<Output>
{

    // instead of the primary constructor above, make a constructr here that still calls the base constructor
    public ConsoleAgent(IAgentRuntime context, [FromKeyedServices("EventTypes")] EventTypes typeRegistry) : base(context, typeRegistry)
    {
        _route = "console";
    }
    public override async Task Handle(Input item)
    {
        Console.WriteLine("Please enter input:");
        string content = Console.ReadLine() ?? string.Empty;

        await ProcessInput(content);

        var evt = new InputProcessed
        {
            Route = _route
        };
        await PublishMessageAsync(evt);
    }

    public override async Task Handle(Output item)
    {
        // Assuming item has a property `Content` that we want to write to the console
        Console.WriteLine(item.Message);
        await ProcessOutput(item.Message);

        var evt = new OutputWritten
        {
            Route = _route
        };
        await PublishMessageAsync(evt);
    }

    public override Task<string> ProcessInput(string message)
    {
        // Implement your input processing logic here
        return Task.FromResult(message);
    }

    public override Task ProcessOutput(string message)
    {
        // Implement your output processing logic here
        return Task.CompletedTask;
    }
}

public interface IUseConsole
{
    public Task ProcessOutput(string message);
}
