// Copyright (c) Microsoft Corporation. All rights reserved.
// IHandleConsole.cs
using Google.Protobuf;
using Microsoft.AutoGen.Contracts;

namespace Microsoft.AutoGen.Agents;
/// <summary>
/// Default interface methods for an event handler for Input and Output that writes or reads from the console
/// Can be used inside your agents by inheriting from this interface
/// public class MyAgent : BaseAgent, IHandleConsole
/// </summary>
public interface IHandleConsole : IHandle<Output>, IHandle<Input>, IProcessIO
{
    /// <summary>
    /// Prototype for Publish Message Async method
    /// </summary>
    /// <typeparam name="T"></typeparam>
    /// <param name="message"></param>
    /// <param name="topic"></param>
    /// <param name="messageId"></param>
    /// <param name="token"></param>
    /// <returns>ValueTask</returns>
    ValueTask PublishMessageAsync<T>(T message, TopicId topic, string? messageId, CancellationToken token = default) where T : IMessage;

    /// <summary>
    /// Receives events of type Output and writes them to the console
    /// then runs the ProcessOutputAsync method which you should implement in your agent
    /// </summary>
    /// <param name="item"></param>
    /// <param name="messageContext"></param>
    /// <returns>ValueTask</returns>
    async ValueTask IHandle<Output>.HandleAsync(Output item, MessageContext messageContext)
    {
        // Assuming item has a property `Message` that we want to write to the console
        Console.WriteLine(item.Message);
        await ProcessOutputAsync(item.Message);

        var evt = new OutputWritten
        {
            Route = "console"
        };
        await PublishMessageAsync(evt, new TopicId("OutputWritten"), null, token: CancellationToken.None).ConfigureAwait(false);
    }

    /// <summary>
    /// Receives events of type Input and reads from the console, then runs the ProcessInputAsync method
    /// which you should implement in your agent
    /// </summary>
    /// <param name="item"></param>
    /// <param name="messageContext"></param>
    /// <returns></returns>
    async ValueTask IHandle<Input>.HandleAsync(Input item, MessageContext messageContext)
    {
        Console.WriteLine("Please enter input:");
        string content = Console.ReadLine() ?? string.Empty;

        await ProcessInputAsync(content);

        var evt = new InputProcessed
        {
            Route = "console"
        };
        await PublishMessageAsync(evt, new TopicId("InputProcessed"), null, token: CancellationToken.None).ConfigureAwait(false);
    }
}
