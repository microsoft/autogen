using Microsoft.AutoGen.Agents.Abstractions;
using Microsoft.Extensions.DependencyInjection;

namespace Microsoft.AutoGen.Agents.Worker.Client;

public class ConsoleAgent : IOAgent<AgentState>,
        IUseConsole,
        IHandle<Input>,
        IHandle<Output>
{

    // instead of the primary constructor above, make a constructr here that still calls the base constructor
    public ConsoleAgent(IAgentContext context,  [FromKeyedServices("EventTypes")] EventTypes typeRegistry) : base(context, typeRegistry)
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
        }.ToCloudEvent(this.AgentId.Key);
        await PublishEvent(evt);
    }

    public override async Task Handle(Output item)
    {
        // Assuming item has a property `Content` that we want to write to the console
        Console.WriteLine(item.Message);

        var evt = new OutputWritten
        {
            Route = _route
        }.ToCloudEvent(this.AgentId.Key);
        await PublishEvent(evt);
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