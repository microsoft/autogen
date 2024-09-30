// Copyright (c) Microsoft Corporation. All rights reserved.
// FunctionCallMiddleware.cs

using System;
using System.Collections.Generic;
using System.Linq;
using System.Runtime.CompilerServices;
using System.Threading;
using System.Threading.Tasks;

namespace AutoGen.Core;

/// <summary>
/// The middleware that process function call message that both send to an agent or reply from an agent.
/// <para>If the last message is <see cref="ToolCallMessage"/> and the tool calls is available in this middleware's function map,
/// the tools from the last message will be invoked and a <see cref="ToolCallResultMessage"/> will be returned. In this situation,
/// the inner agent will be short-cut and won't be invoked.</para>
/// <para>Otherwise, the message will be sent to the inner agent. In this situation</para>
/// <para>if the reply from the inner agent is <see cref="ToolCallMessage"/>,
/// and the tool calls is available in this middleware's function map, the tools from the reply will be invoked,
/// and a <see cref="ToolCallAggregateMessage"/> will be returned.
/// </para>
/// <para>If the reply from the inner agent is <see cref="ToolCallMessage"/> but the tool calls is not available in this middleware's function map,
/// or the reply from the inner agent is not <see cref="ToolCallMessage"/>, the original reply from the inner agent will be returned.</para>
/// <para>
/// When used as a streaming middleware, if the streaming reply from the inner agent is <see cref="ToolCallMessageUpdate"/> or <see cref="TextMessageUpdate"/>,
/// This middleware will update the message accordingly and invoke the function if the tool call is available in this middleware's function map.
/// If the streaming reply from the inner agent is other types of message, the most recent message will be used to invoke the function.
/// </para>
/// </summary>
public class FunctionCallMiddleware : IStreamingMiddleware
{
    private readonly IEnumerable<FunctionContract>? functions;
    private readonly IDictionary<string, Func<string, Task<string>>>? functionMap;

    public FunctionCallMiddleware(
        IEnumerable<FunctionContract>? functions = null,
        IDictionary<string, Func<string, Task<string>>>? functionMap = null,
        string? name = null)
    {
        this.Name = name ?? nameof(FunctionCallMiddleware);
        this.functions = functions;
        this.functionMap = functionMap;
    }

    public string? Name { get; }

    public async Task<IMessage> InvokeAsync(MiddlewareContext context, IAgent agent, CancellationToken cancellationToken = default)
    {
        var lastMessage = context.Messages.Last();
        if (lastMessage is ToolCallMessage toolCallMessage)
        {
            return await this.InvokeToolCallMessagesBeforeInvokingAgentAsync(toolCallMessage, agent);
        }

        // combine functions
        var options = new GenerateReplyOptions(context.Options ?? new GenerateReplyOptions());
        var combinedFunctions = this.functions?.Concat(options.Functions ?? []) ?? options.Functions;
        options.Functions = combinedFunctions?.ToArray();

        var reply = await agent.GenerateReplyAsync(context.Messages, options, cancellationToken);

        // if the reply is a function call message plus the function's name is available in function map, invoke the function and return the result instead of sending to the agent.
        if (reply is ToolCallMessage toolCallMsg)
        {
            return await this.InvokeToolCallMessagesAfterInvokingAgentAsync(toolCallMsg, agent);
        }

        // for all other messages, just return the reply from the agent.
        return reply;
    }

    public async IAsyncEnumerable<IMessage> InvokeAsync(
        MiddlewareContext context,
        IStreamingAgent agent,
        [EnumeratorCancellation] CancellationToken cancellationToken = default)
    {
        var lastMessage = context.Messages.Last();
        if (lastMessage is ToolCallMessage toolCallMessage)
        {
            yield return await this.InvokeToolCallMessagesBeforeInvokingAgentAsync(toolCallMessage, agent);
        }

        // combine functions
        var options = new GenerateReplyOptions(context.Options ?? new GenerateReplyOptions());
        var combinedFunctions = this.functions?.Concat(options.Functions ?? []) ?? options.Functions;
        options.Functions = combinedFunctions?.ToArray();

        IMessage? mergedFunctionCallMessage = default;
        await foreach (var message in agent.GenerateStreamingReplyAsync(context.Messages, options, cancellationToken))
        {
            if (message is ToolCallMessageUpdate toolCallMessageUpdate && this.functionMap != null)
            {
                if (mergedFunctionCallMessage is null)
                {
                    mergedFunctionCallMessage = new ToolCallMessage(toolCallMessageUpdate);
                }
                else if (mergedFunctionCallMessage is ToolCallMessage toolCall)
                {
                    toolCall.Update(toolCallMessageUpdate);
                }
                else
                {
                    throw new InvalidOperationException("The first message is ToolCallMessage, but the update message is not ToolCallMessageUpdate");
                }
            }
            else if (message is ToolCallMessage toolCallMessage1)
            {
                mergedFunctionCallMessage = toolCallMessage1;
            }
            else
            {
                yield return message;
            }
        }

        if (mergedFunctionCallMessage is ToolCallMessage toolCallMsg)
        {
            yield return await this.InvokeToolCallMessagesAfterInvokingAgentAsync(toolCallMsg, agent);
        }
    }

    private async Task<ToolCallResultMessage> InvokeToolCallMessagesBeforeInvokingAgentAsync(ToolCallMessage toolCallMessage, IAgent agent)
    {
        var toolCallResult = new List<ToolCall>();
        var toolCalls = toolCallMessage.ToolCalls;
        foreach (var toolCall in toolCalls)
        {
            var functionName = toolCall.FunctionName;
            var functionArguments = toolCall.FunctionArguments;
            if (this.functionMap?.TryGetValue(functionName, out var func) is true)
            {
                var result = await func(functionArguments);
                toolCallResult.Add(new ToolCall(functionName, functionArguments, result) { ToolCallId = toolCall.ToolCallId });
            }
            else if (this.functionMap is not null)
            {
                var errorMessage = $"Function {functionName} is not available. Available functions are: {string.Join(", ", this.functionMap.Select(f => f.Key))}";

                toolCallResult.Add(new ToolCall(functionName, functionArguments, errorMessage) { ToolCallId = toolCall.ToolCallId });
            }
            else
            {
                throw new InvalidOperationException("FunctionMap is not available");
            }
        }

        return new ToolCallResultMessage(toolCallResult, from: agent.Name);
    }

    private async Task<IMessage> InvokeToolCallMessagesAfterInvokingAgentAsync(ToolCallMessage toolCallMsg, IAgent agent)
    {
        var toolCallsReply = toolCallMsg.ToolCalls;
        var toolCallResult = new List<ToolCall>();
        foreach (var toolCall in toolCallsReply)
        {
            var fName = toolCall.FunctionName;
            var fArgs = toolCall.FunctionArguments;
            if (this.functionMap?.TryGetValue(fName, out var func) is true)
            {
                var result = await func(fArgs);
                toolCallResult.Add(new ToolCall(fName, fArgs, result) { ToolCallId = toolCall.ToolCallId });
            }
        }

        if (toolCallResult.Count > 0)
        {
            var toolCallResultMessage = new ToolCallResultMessage(toolCallResult, from: agent.Name);
            return new ToolCallAggregateMessage(toolCallMsg, toolCallResultMessage, from: agent.Name);
        }
        else
        {
            return toolCallMsg;
        }
    }
}
