// Copyright (c) Microsoft Corporation. All rights reserved.
// ToolCallResultMessage.cs

using System.Collections.Generic;
using System.Linq;
using System.Text;

namespace AutoGen.Core;

public class ToolCallResultMessage : IMessage, ICanGetTextContent
{
    public ToolCallResultMessage(IEnumerable<ToolCall> toolCalls, string? from = null)
    {
        this.From = from;
        this.ToolCalls = toolCalls.ToList();
    }

    public ToolCallResultMessage(string result, string functionName, string functionArgs, string? from = null)
    {
        this.From = from;
        var toolCall = new ToolCall(functionName, functionArgs) { ToolCallId = functionName };
        toolCall.Result = result;
        this.ToolCalls = [toolCall];
    }

    /// <summary>
    /// The original tool call message
    /// </summary>
    public IList<ToolCall> ToolCalls { get; set; }

    public string? From { get; set; }

    public string? GetContent()
    {
        var results = this.ToolCalls
            .Where(x => x.Result != null)
            .Select(x => x.Result);

        return string.Join("\n", results);
    }

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
}
