using Microsoft.AutoGen.Abstractions;

namespace Microsoft.AutoGen.Agents
{
    public interface IHandleConsole : IHandle<Output>, IHandle<Input>
    {
        string Route { get; }
        AgentId AgentId { get; }
        ValueTask PublishEvent(CloudEvent item);

        async Task IHandle<Output>.Handle(Output item)
        {
            // Assuming item has a property `Message` that we want to write to the console
            Console.WriteLine(item.Message);
            await ProcessOutput(item.Message);

            var evt = new OutputWritten
            {
                Route = "console"
            }.ToCloudEvent(AgentId.Key);
            await PublishEvent(evt);
        }
        async Task IHandle<Input>.Handle(Input item)
        {
            Console.WriteLine("Please enter input:");
            string content = Console.ReadLine() ?? string.Empty;

            await ProcessInput(content);

            var evt = new InputProcessed
            {
                Route = "console"
            }.ToCloudEvent(AgentId.Key);
            await PublishEvent(evt);
        }
        static Task ProcessOutput(string message)
        {
            // Implement your output processing logic here
            return Task.CompletedTask;
        }
        static Task<string> ProcessInput(string message)
        {
            // Implement your input processing logic here
            return Task.FromResult(message);
        }
    }
}
