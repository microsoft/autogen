using Microsoft.AutoGen.Agents.Abstractions;
using Microsoft.Extensions.Logging;

namespace Microsoft.AutoGen.Agents.Client;

[TopicSubscription("FileIO")]
public class FileAgent : IOAgent<AgentState>,
        IUseFiles,
        IHandle<Input>,
        IHandle<Output>
{
    public FileAgent(IAgentContext context, EventTypes typeRegistry, string filePath) : base(context, typeRegistry)
    {
        _filePath = filePath;
    }
    private readonly string _filePath;

    public override async Task Handle(Input item)
    {

        // validate that the file exists
        if (!File.Exists(_filePath))
        {
            string errorMessage = $"File not found: {_filePath}";
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
        using (var writer = new StreamWriter(_filePath, append: true))
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