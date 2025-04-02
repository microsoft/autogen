// Copyright (c) Microsoft Corporation. All rights reserved.
// PrintMessageMiddleware.cs

using System;
using System.Collections.Generic;
using System.Runtime.CompilerServices;
using System.Threading;
using System.Threading.Tasks;

namespace AutoGen.Core;

/// <summary>
/// The middleware that prints the reply from agent to the console.
/// </summary>
public class PrintMessageMiddleware : IStreamingMiddleware
{
    public string? Name => nameof(PrintMessageMiddleware);

    public async Task<IMessage> InvokeAsync(MiddlewareContext context, IAgent agent, CancellationToken cancellationToken = default)
    {
        if (agent is IStreamingAgent streamingAgent)
        {
            IMessage? recentUpdate = null;
            await foreach (var message in this.InvokeAsync(context, streamingAgent, cancellationToken))
            {
                if (message is IMessage imessage)
                {
                    recentUpdate = imessage;
                }
            }
            Console.WriteLine();
            if (recentUpdate is not null && recentUpdate is not TextMessage)
            {
                Console.WriteLine(recentUpdate.FormatMessage());
            }

            return recentUpdate ?? throw new InvalidOperationException("The message is not a valid message");
        }
        else
        {
            var reply = await agent.GenerateReplyAsync(context.Messages, context.Options, cancellationToken);

            var formattedMessages = reply.FormatMessage();

            Console.WriteLine(formattedMessages);

            return reply;
        }
    }

    public async IAsyncEnumerable<IMessage> InvokeAsync(MiddlewareContext context, IStreamingAgent agent, [EnumeratorCancellation] CancellationToken cancellationToken = default)
    {
        IMessage? recentUpdate = null;
        await foreach (var message in agent.GenerateStreamingReplyAsync(context.Messages, context.Options, cancellationToken))
        {
            if (message is TextMessageUpdate textMessageUpdate)
            {
                if (recentUpdate is null)
                {
                    // Print from: xxx
                    Console.WriteLine($"from: {textMessageUpdate.From}");
                    recentUpdate = new TextMessage(textMessageUpdate);
                    Console.Write(textMessageUpdate.Content);

                    yield return message;
                }
                else if (recentUpdate is TextMessage recentTextMessage)
                {
                    // Print the content of the message
                    Console.Write(textMessageUpdate.Content);
                    recentTextMessage.Update(textMessageUpdate);

                    yield return recentTextMessage;
                }
                else
                {
                    throw new InvalidOperationException("The recent update is not a TextMessage");
                }
            }
            else if (message is ToolCallMessageUpdate toolCallUpdate)
            {
                if (recentUpdate is null)
                {
                    recentUpdate = new ToolCallMessage(toolCallUpdate);

                    yield return message;
                }
                else if (recentUpdate is ToolCallMessage recentToolCallMessage)
                {
                    recentToolCallMessage.Update(toolCallUpdate);

                    yield return message;
                }
                else
                {
                    throw new InvalidOperationException("The recent update is not a ToolCallMessage");
                }
            }
            else if (message is IMessage imessage)
            {
                recentUpdate = imessage;

                yield return imessage;
            }
            else
            {
                throw new InvalidOperationException("The message is not a valid message");
            }
        }
        Console.WriteLine();
        if (recentUpdate is not null && recentUpdate is not TextMessage)
        {
            Console.WriteLine(recentUpdate.FormatMessage());
        }

        yield return recentUpdate ?? throw new InvalidOperationException("The message is not a valid message");
    }
}
