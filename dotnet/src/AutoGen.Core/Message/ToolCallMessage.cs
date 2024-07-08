// Copyright (c) Microsoft Corporation. All rights reserved.
// ToolCallMessage.cs

using System.Collections.Generic;
using System.Linq;
using System.Text;

namespace AutoGen.Core;

public class ToolCall
{
    public ToolCall(string functionName, string functionArgs)
    {
        this.FunctionName = functionName;
        this.FunctionArguments = functionArgs;
    }

    public ToolCall(string functionName, string functionArgs, string result)
    {
        this.FunctionName = functionName;
        this.FunctionArguments = functionArgs;
        this.Result = result;
    }

    public string FunctionName { get; set; }

    public string FunctionArguments { get; set; }

    public string? ToolCallId { get; set; }

    public string? Result { get; set; }

    public override string ToString()
    {
        return $"ToolCall({this.FunctionName}, {this.FunctionArguments}, {this.Result})";
    }
}

public class ToolCallMessage : IMessage, ICanGetToolCalls, ICanGetTextContent
{
    public ToolCallMessage(IEnumerable<ToolCall> toolCalls, string? from = null)
    {
        this.From = from;
        this.ToolCalls = toolCalls.ToList();
    }

    public ToolCallMessage(string functionName, string functionArgs, string? from = null)
    {
        this.From = from;
        this.ToolCalls = new List<ToolCall> { new ToolCall(functionName, functionArgs) { ToolCallId = functionName } };
    }

    public ToolCallMessage(ToolCallMessageUpdate update)
    {
        this.From = update.From;
        this.ToolCalls = new List<ToolCall> { new ToolCall(update.FunctionName, update.FunctionArgumentUpdate) };
    }

    public void Update(ToolCallMessageUpdate update)
    {
        // firstly, valid if the update is from the same agent
        if (update.From != this.From)
        {
            throw new System.ArgumentException("From mismatch", nameof(update));
        }

        // if update.FunctionName exists in the tool calls, update the function arguments
        var toolCall = this.ToolCalls.FirstOrDefault(tc => tc.FunctionName == update.FunctionName);
        if (toolCall is not null)
        {
            toolCall.FunctionArguments += update.FunctionArgumentUpdate;
        }
        else
        {
            this.ToolCalls.Add(new ToolCall(update.FunctionName, update.FunctionArgumentUpdate));
        }
    }

    public IList<ToolCall> ToolCalls { get; set; }

    public string? From { get; set; }

    /// <summary>
    /// Some LLMs might also include text content in a tool call response, like GPT.
    /// This field is used to store the text content in that case.
    /// </summary>
    public string? Content { get; set; }

    public override string ToString()
    {
        var sb = new StringBuilder();
        sb.Append($"ToolCallMessage({this.From})");
        foreach (var toolCall in this.ToolCalls)
        {
            sb.Append($"\n\t{toolCall}");
        }

        return sb.ToString();
    }

    public IEnumerable<ToolCall> GetToolCalls()
    {
        return this.ToolCalls;
    }

    public string? GetContent()
    {
        return this.Content;
    }
}

public class ToolCallMessageUpdate : IMessage
{
    public ToolCallMessageUpdate(string functionName, string functionArgumentUpdate, string? from = null)
    {
        this.From = from;
        this.FunctionName = functionName;
        this.FunctionArgumentUpdate = functionArgumentUpdate;
    }

    public string? From { get; set; }

    public string FunctionName { get; set; }

    public string FunctionArgumentUpdate { get; set; }
}
