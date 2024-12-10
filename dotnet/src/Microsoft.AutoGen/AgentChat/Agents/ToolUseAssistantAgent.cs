// Copyright (c) Microsoft Corporation. All rights reserved.
// ToolUseAssistantAgent.cs

using Microsoft.AutoGen.AgentChat.Abstractions;
using Microsoft.Extensions.AI;

namespace Microsoft.AutoGen.AgentChat.Agents;
internal sealed class ToolUseAssistantAgent : AssistantAgent
{
    private const string DefaultDescription = "An agent that provides assistance with ability to use tools.";
    private const string DefaultSystemPrompt = "You are a helpful AI assistant. Solve tasks using your tools. Reply with 'TERMINATE' when the task has been completed.";

    [Obsolete("ToolUseAssistantAgent is deprecated. Use AssistantAgent instead.")]
    public ToolUseAssistantAgent(string name, IChatClient modelClient, IEnumerable<ITool> registeredTools, string description = DefaultDescription, string systemPrompt = DefaultSystemPrompt) : base(name, modelClient, description, systemPrompt, tools: registeredTools)
    {
    }
}
