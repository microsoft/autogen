// Copyright (c) Microsoft Corporation. All rights reserved.
// RolePlayToolCallOrchestrator.cs

using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using AutoGen.OpenAI.Extension;
using OpenAI.Chat;

namespace AutoGen.OpenAI.Orchestrator;

/// <summary>
/// Orchestrating group chat using role play tool call
/// </summary>
public partial class RolePlayToolCallOrchestrator : IOrchestrator
{
    public readonly ChatClient chatClient;
    private readonly Graph? workflow;

    public RolePlayToolCallOrchestrator(ChatClient chatClient, Graph? workflow = null)
    {
        this.chatClient = chatClient;
        this.workflow = workflow;
    }

    public async Task<IAgent?> GetNextSpeakerAsync(
        OrchestrationContext context,
        CancellationToken cancellationToken = default)
    {
        var candidates = context.Candidates.ToList();

        if (candidates.Count == 0)
        {
            return null;
        }

        if (candidates.Count == 1)
        {
            return candidates.First();
        }

        // if there's a workflow
        // and the next available agent from the workflow is in the group chat
        // then return the next agent from the workflow
        if (this.workflow != null)
        {
            var lastMessage = context.ChatHistory.LastOrDefault();
            if (lastMessage == null)
            {
                return null;
            }
            var currentSpeaker = candidates.First(candidates => candidates.Name == lastMessage.From);
            var nextAgents = await this.workflow.TransitToNextAvailableAgentsAsync(currentSpeaker, context.ChatHistory, cancellationToken);
            nextAgents = nextAgents.Where(nextAgent => candidates.Any(candidate => candidate.Name == nextAgent.Name));
            candidates = nextAgents.ToList();
            if (!candidates.Any())
            {
                return null;
            }

            if (candidates is { Count: 1 })
            {
                return candidates.First();
            }
        }

        // In this case, since there are more than one available agents from the workflow for the next speaker
        // We need to invoke LLM to select the next speaker via select next speaker function

        var chatHistoryStringBuilder = new StringBuilder();
        foreach (var message in context.ChatHistory)
        {
            var chatHistoryPrompt = $"{message.From}: {message.GetContent()}";

            chatHistoryStringBuilder.AppendLine(chatHistoryPrompt);
        }

        var chatHistory = chatHistoryStringBuilder.ToString();

        var prompt = $"""
            # Task: Select the next speaker

            You are in a role-play game. Carefully read the conversation history and select the next speaker from the available roles.

            # Conversation
            {chatHistory}

            # Available roles
            - {string.Join(",", candidates.Select(candidate => candidate.Name))}

            Select the next speaker from the available roles and provide a reason for your selection.
            """;

        // enforce the next speaker to be selected by the LLM
        var option = new ChatCompletionOptions
        {
            ToolChoice = ChatToolChoice.CreateFunctionChoice(this.SelectNextSpeakerFunctionContract.Name),
        };

        option.Tools.Add(this.SelectNextSpeakerFunctionContract.ToChatTool());
        var toolCallMiddleware = new FunctionCallMiddleware(
            functions: [this.SelectNextSpeakerFunctionContract],
            functionMap: new Dictionary<string, Func<string, Task<string>>>
            {
                [this.SelectNextSpeakerFunctionContract.Name] = this.SelectNextSpeakerWrapper,
            });

        var selectAgent = new OpenAIChatAgent(
            chatClient,
            "admin",
            option)
            .RegisterMessageConnector()
            .RegisterMiddleware(toolCallMiddleware);

        var reply = await selectAgent.SendAsync(prompt);

        var nextSpeaker = candidates.FirstOrDefault(candidate => candidate.Name == reply.GetContent());

        return nextSpeaker;
    }

    /// <summary>
    /// Select the next speaker by name and reason
    /// </summary>
    [Function]
    public async Task<string> SelectNextSpeaker(string name, string reason)
    {
        return name;
    }
}
