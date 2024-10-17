using Microsoft.AutoGen.Abstractions;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;

namespace Microsoft.AutoGen.Agents;

[TopicSubscription("FileIO")]
public abstract class FileAgent(
    IAgentContext context,
    [FromKeyedServices("EventTypes")] EventTypes typeRegistry,
    string inputPath = "input.txt",
    string outputPath = "output.txt"
    ) : IOAgent<AgentState>(context, typeRegistry),
        IUseFiles,
        IHandle<Input>,
        IHandle<Output>
{
    public override async Task Handle(Input item)
    {
        // validate that the file exists
        if (!File.Exists(inputPath))
        {
            var errorMessage = $"File not found: {inputPath}";
            Logger.LogError(errorMessage);
            //publish IOError event
            var err = new IOError
            {
                Message = errorMessage
            }.ToCloudEvent(this.AgentId.Key);
            await PublishEvent(err);
            return;
        }
        string content;
        using (var reader = new StreamReader(item.Message))
        {
            content = await reader.ReadToEndAsync();
        }
        await ProcessInput(content);
        var evt = new InputProcessed
        {
            Route = _route
        }.ToCloudEvent(this.AgentId.Key);
        await PublishEvent(evt);
    }
    public override async Task Handle(Output item)
    {
        using (var writer = new StreamWriter(outputPath, append: true))
        {
            await writer.WriteLineAsync(item.Message);
        }
        var evt = new OutputWritten
        {
            Route = _route
        }.ToCloudEvent(this.AgentId.Key);
        await PublishEvent(evt);
    }
    public override async Task<string> ProcessInput(string message)
    {
        var evt = new InputProcessed
        {
            Route = _route,
        }.ToCloudEvent(this.AgentId.Key);
        await PublishEvent(evt);
        return message;
    }
    public override Task ProcessOutput(string message)
    {
        // Implement your output processing logic here
        return Task.CompletedTask;
    }
}
public interface IUseFiles
{
}
