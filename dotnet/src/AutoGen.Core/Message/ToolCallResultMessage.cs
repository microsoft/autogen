// Copyright (c) Microsoft Corporation. All rights reserved.
// ToolCallResultMessage.cs

using System.Collections.Generic;
using System.Linq;
using System.Text;

namespace AutoGen.Core;

public class ToolCallResultMessage : IMessage
{
    public ToolCallResultMessage(IEnumerable<ToolCall> toolCalls, string? from = null)
    {
        this.From = from;
        this.ToolCalls = toolCalls.ToList();
    }

    public ToolCallResultMessage(string result, string functionName, string functionArgs, string? from = null)
    {
        this.From = from;
        var toolCall = new ToolCall(functionName, functionArgs);
        toolCall.Result = result;
        this.ToolCalls = [toolCall];
    }

    /// <summary>
    /// The original tool call message
    /// </summary>
    public IList<ToolCall> ToolCalls { get; set; }

    public string? From { get; set; }

    public override string ToString()
    {
        var sb = new StringBuilder();
        sb.Append($"ToolCallResultMessage({this.From})");
        foreach (var toolCall in this.ToolCalls)
        {
            sb.Append($"\n\t{toolCall}");
        }

        return sb.ToString();
    }

    private void Validate()
    {
        // each tool call must have a result
        foreach (var toolCall in this.ToolCalls)
        {
            if (string.IsNullOrEmpty(toolCall.Result))
            {
                throw new System.ArgumentException($"The tool call {toolCall} does not have a result");
            }
        }
    }
}
