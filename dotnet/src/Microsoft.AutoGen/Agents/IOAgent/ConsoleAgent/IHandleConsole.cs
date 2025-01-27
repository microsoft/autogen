// Copyright (c) Microsoft Corporation. All rights reserved.
// IHandleConsole.cs

using Google.Protobuf;
using Microsoft.AutoGen.Contracts;
using Microsoft.AutoGen.Core;

namespace Microsoft.AutoGen.Agents;

public interface IHandleConsole : IHandle<Output>, IHandle<Input>
{
    AgentId AgentId { get; }
    ValueTask PublishMessageAsync<T>(T message, CancellationToken token = default) where T : IMessage;

    async Task IHandle<Output>.Handle(Output item, CancellationToken cancellationToken)
    {
        // Assuming item has a property `Message` that we want to write to the console
        Console.WriteLine(item.Message);
        await ProcessOutput(item.Message);

        var evt = new OutputWritten
        {
            Route = "console"
        };
        await PublishMessageAsync(evt).ConfigureAwait(false);
    }
    async Task IHandle<Input>.Handle(Input item, CancellationToken cancellationToken)
    {
        Console.WriteLine("Please enter input:");
        string content = Console.ReadLine() ?? string.Empty;

        await ProcessInput(content);

        var evt = new InputProcessed
        {
            Route = "console"
        };
        await PublishMessageAsync(evt).ConfigureAwait(false);
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
