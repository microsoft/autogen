// Copyright (c) Microsoft Corporation. All rights reserved.
// HumanInputMiddleware.cs

using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;

namespace AutoGen;

/// <summary>
/// the middleware to get human input
/// </summary>
public class HumanInputMiddleware : IMiddleware
{
    private readonly HumanInputMode mode;
    private readonly string prompt;
    private readonly string exitKeyword;
    private Func<IEnumerable<IMessage>, CancellationToken, Task<bool>> isTermination;
    private Func<string?> getInput = Console.ReadLine;
    private Action<string> writeLine = Console.WriteLine;
    public string? Name => nameof(HumanInputMiddleware);

    public HumanInputMiddleware(
        string prompt = "Please give feedback: Press enter or type 'exit' to stop the conversation.",
        string exitKeyword = "exit",
        HumanInputMode mode = HumanInputMode.AUTO,
        Func<IEnumerable<IMessage>, CancellationToken, Task<bool>>? isTermination = null,
        Func<string?>? getInput = null,
        Action<string>? writeLine = null)
    {
        this.prompt = prompt;
        this.isTermination = isTermination ?? DefaultIsTermination;
        this.exitKeyword = exitKeyword;
        this.mode = mode;
        this.getInput = getInput ?? GetInput;
        this.writeLine = writeLine ?? WriteLine;
    }

    public async Task<IMessage> InvokeAsync(MiddlewareContext context, IAgent agent, CancellationToken cancellationToken = default)
    {
        // if the mode is never, then just return the input message
        if (mode == HumanInputMode.NEVER)
        {
            return await agent.GenerateReplyAsync(context.Messages, context.Options, cancellationToken);
        }

        // if the mode is always, then prompt the user for input
        if (mode == HumanInputMode.ALWAYS)
        {
            this.writeLine(prompt);
            var input = getInput();
            if (input == exitKeyword)
            {
                return new TextMessage(Role.Assistant, GroupChatExtension.TERMINATE, agent.Name);
            }

            input ??= string.Empty;

            return new TextMessage(Role.Assistant, input, agent.Name);
        }

        // if the mode is auto, then prompt the user for input if the message is not a termination message
        if (mode == HumanInputMode.AUTO)
        {
            if (await isTermination(context.Messages, cancellationToken) is false)
            {
                return await agent.GenerateReplyAsync(context.Messages, context.Options, cancellationToken);
            }

            this.writeLine(prompt);
            var input = getInput();
            if (input == exitKeyword)
            {
                return new TextMessage(Role.Assistant, GroupChatExtension.TERMINATE, agent.Name);
            }

            input ??= string.Empty;

            return new TextMessage(Role.Assistant, input, agent.Name);
        }

        throw new InvalidOperationException("Invalid mode");
    }

    private async Task<bool> DefaultIsTermination(IEnumerable<IMessage> messages, CancellationToken _)
    {
        return messages?.Last().IsGroupChatTerminateMessage() is true;
    }

    private string? GetInput()
    {
        return Console.ReadLine();
    }

    private void WriteLine(string message)
    {
        Console.WriteLine(message);
    }
}
