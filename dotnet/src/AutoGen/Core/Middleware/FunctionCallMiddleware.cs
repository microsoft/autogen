// Copyright (c) Microsoft Corporation. All rights reserved.
// FunctionCallMiddleware.cs

using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using Azure.AI.OpenAI;

namespace AutoGen.Core.Middleware;

/// <summary>
/// The middleware that process function call message that both send to an agent or reply from an agent.
/// </summary>
public class FunctionCallMiddleware : IMiddleware
{
    private readonly IEnumerable<FunctionDefinition>? functions;
    private readonly IDictionary<string, Func<string, Task<string>>>? functionMap;
    public FunctionCallMiddleware(
        IEnumerable<FunctionDefinition>? functions = null,
        IDictionary<string, Func<string, Task<string>>>? functionMap = null,
        string? name = null)
    {
        this.Name = name ?? nameof(FunctionCallMiddleware);
        this.functions = functions;
        this.functionMap = functionMap;
    }

    public string? Name { get; }

    public async Task<Message> InvokeAsync(MiddlewareContext context, IAgent agent, CancellationToken cancellationToken = default)
    {
        // if the last message is a function call message, invoke the function and return the result instead of sending to the agent.
        var lastMessage = context.Messages.Last();
        if (lastMessage is not null && lastMessage is { FunctionName: string functionName, FunctionArguments: string functionArguments })
        {
            if (this.functionMap?.TryGetValue(functionName, out var func) is true)
            {
                var result = await func(functionArguments);
                return new Message(role: Role.Function, content: result, from: lastMessage.From)
                {
                    FunctionName = functionName,
                    FunctionArguments = functionArguments,
                };
            }
            else
            {
                var errorMessage = $"Function {functionName} is not available. Available functions are: {string.Join(", ", this.functionMap.Select(f => f.Key))}";

                return new Message(role: Role.Function, content: errorMessage, from: lastMessage.From)
                {
                    FunctionName = functionName,
                    FunctionArguments = functionArguments,
                };
            }
        }

        // combine functions
        var options = new GenerateReplyOptions(context.Options ?? new GenerateReplyOptions());
        var combinedFunctions = this.functions?.Concat(options.Functions ?? []) ?? options.Functions;
        options.Functions = combinedFunctions?.ToArray();

        var reply = await agent.GenerateReplyAsync(context.Messages, options, cancellationToken);

        // if the reply is a function call message plus the function's name is available in function map, invoke the function and return the result instead of sending to the agent.
        if (reply is { FunctionName: string fName, FunctionArguments: string fArgs })
        {
            if (this.functionMap?.TryGetValue(fName, out var func) is true)
            {
                var result = await func(fArgs);
                return new Message(role: Role.Assistant, content: result, from: reply.From)
                {
                    FunctionName = fName,
                    FunctionArguments = fArgs,
                };
            }
        }

        // for all other messages, just return the reply from the agent.
        return reply;
    }
}
