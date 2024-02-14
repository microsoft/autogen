// Copyright (c) Microsoft Corporation. All rights reserved.
// ToolCallMessage.cs

using System.Collections.Generic;
using System.Text;

namespace AutoGen;

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

    public string? Result { get; set; }

    public override string ToString()
    {
        return $"ToolCall({this.FunctionName}, {this.FunctionArguments}, {this.Result})";
    }
}

public class ToolCallMessage : IMessage
{
    public ToolCallMessage(IEnumerable<ToolCall> toolCalls, string? from = null)
    {
        this.From = from;
        this.ToolCalls = toolCalls;
    }

    public ToolCallMessage(string functionName, string functionArgs, string? from = null)
    {
        this.From = from;
        this.ToolCalls = new List<ToolCall> { new ToolCall(functionName, functionArgs) };
    }

    public IEnumerable<ToolCall> ToolCalls { get; set; }

    public string? From { get; set; }

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
}
