// Copyright (c) Microsoft Corporation. All rights reserved.
// PrintMessageMiddleware.cs

using System;
using System.Threading;
using System.Threading.Tasks;

namespace AutoGen.Core.Middleware;

/// <summary>
/// The middleware that prints the reply from agent to the console.
/// </summary>
public class PrintMessageMiddleware : IMiddleware
{
    public string? Name => nameof(PrintMessageMiddleware);

    public async Task<Message> InvokeAsync(MiddlewareContext context, IAgent agent, CancellationToken cancellationToken = default)
    {
        var reply = await agent.GenerateReplyAsync(context.Messages, context.Options, cancellationToken);

        var formattedMessages = reply.FormatMessage();

        Console.WriteLine(formattedMessages);

        return reply;
    }
}
