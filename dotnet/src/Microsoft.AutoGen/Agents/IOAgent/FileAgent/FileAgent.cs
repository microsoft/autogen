// Copyright (c) Microsoft Corporation. All rights reserved.
// FileAgent.cs
using Microsoft.AutoGen.Contracts;
using Microsoft.AutoGen.Core;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;

namespace Microsoft.AutoGen.Agents;

[TopicSubscription("FileIO")]
public abstract class FileAgent(
    IAgentWorker worker,
    [FromKeyedServices("EventTypes")] EventTypes typeRegistry,
    string inputPath = "input.txt",
    string outputPath = "output.txt"
    ) : IOAgent(worker, typeRegistry),
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
            _logger.LogError(errorMessage);
            //publish IOError event
            var err = new IOError
            {
                Message = errorMessage
            };
            await PublishMessageAsync(err);
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

        };
        await PublishMessageAsync(evt);
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
        };
        await PublishMessageAsync(evt);
    }
    public override async Task<string> ProcessInput(string message)
    {
        var evt = new InputProcessed
        {
            Route = _route,
        };
        await PublishMessageAsync(evt);
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
