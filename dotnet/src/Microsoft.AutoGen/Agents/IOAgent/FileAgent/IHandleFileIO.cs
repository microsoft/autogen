// Copyright (c) Microsoft Corporation. All rights reserved.
// IHandleFileIO.cs
using Microsoft.AutoGen.Contracts;
using Microsoft.Extensions.Logging;

namespace Microsoft.AutoGen.Agents;
/// <summary>
/// Default interface methods for an event handler for Input and Output that writes or reads from a file
/// Can be used inside your agents by inheriting from this interface
/// public class MyAgent : BaseAgent, IHandleFileIO
/// </summary>
public interface IHandleFileIO : IHandle<Input>, IHandle<Output>, IProcessIO
{
    // A Logger instance to log messages
    ILogger LogTarget { get; }
    // The path to the input file
    string InputPath { get; }
    // The path to the output file
    string OutputPath { get; }
    // The route of the agent (used in the post-process events)
    const string Route = "Microsoft.AutoGen.Agents.IHandleFileIO";

    /// <summary>
    /// Prototype for Publish Message Async method
    /// </summary>
    /// <param name="message"></param>
    /// <param name="topic"></param>
    /// <param name="messageId"></param>
    /// <param name="cancellationToken"></param>
    /// <returns>ValueTask</returns>
    ValueTask PublishMessageAsync(object message, TopicId topic, string? messageId = null, CancellationToken cancellationToken = default);
    async ValueTask IHandle<Input>.HandleAsync(Input item, MessageContext messageContext)
    {

        // validate that the file exists
        if (!File.Exists(InputPath))
        {
            var errorMessage = $"File not found: {InputPath}";
            LogTarget.LogError(errorMessage);
            //publish IOError event
            var err = new IOError
            {
                Message = errorMessage
            };
            await PublishMessageAsync(err, new TopicId("IOError"), null, cancellationToken: CancellationToken.None).ConfigureAwait(false);
            return;
        }
        string content;
        using (var reader = new StreamReader(item.Message))
        {
            content = await reader.ReadToEndAsync(CancellationToken.None);
        }
        await ProcessInputAsync(content);
        var evt = new InputProcessed
        {
            Route = Route
        };
        await PublishMessageAsync(evt, new TopicId("InputProcessed"), null, cancellationToken: CancellationToken.None).ConfigureAwait(false);
    }
    async ValueTask IHandle<Output>.HandleAsync(Output item, MessageContext messageContext)
    {
        using (var writer = new StreamWriter(OutputPath, append: true))
        {
            await writer.WriteLineAsync(item.Message);
        }
        var evt = new OutputWritten
        {
            Route = Route
        };
        await PublishMessageAsync(evt, new TopicId("OutputWritten"), null, cancellationToken: CancellationToken.None).ConfigureAwait(false);
    }
}
