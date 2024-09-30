// Copyright (c) Microsoft Corporation. All rights reserved.
// RolePlayOrchestrator.cs

using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;

namespace AutoGen.Core;

public class RolePlayOrchestrator : IOrchestrator
{
    private readonly IAgent admin;
    private readonly Graph? workflow;
    public RolePlayOrchestrator(IAgent admin, Graph? workflow = null)
    {
        this.admin = admin;
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
        // the admin will be invoked to decide the next speaker
        var agentNames = candidates.Select(candidate => candidate.Name);
        var rolePlayMessage = new TextMessage(Role.User,
            content: $@"You are in a role play game. Carefully read the conversation history and carry on the conversation.
The available roles are:
{string.Join(",", agentNames)}

Each message will start with 'From name:', e.g:
From {agentNames.First()}:
//your message//.");

        var chatHistoryWithName = this.ProcessConversationsForRolePlay(context.ChatHistory);
        var messages = new IMessage[] { rolePlayMessage }.Concat(chatHistoryWithName);

        var response = await this.admin.GenerateReplyAsync(
            messages: messages,
            options: new GenerateReplyOptions
            {
                Temperature = 0,
                MaxToken = 128,
                StopSequence = [":"],
                Functions = null,
            },
            cancellationToken: cancellationToken);

        var name = response.GetContent() ?? throw new ArgumentException("No name is returned.");

        // remove From
        name = name!.Substring(5);
        var candidate = candidates.FirstOrDefault(x => x.Name!.ToLower() == name.ToLower());

        if (candidate != null)
        {
            return candidate;
        }

        var errorMessage = $"The response from admin is {name}, which is either not in the candidates list or not in the correct format.";
        throw new ArgumentException(errorMessage);
    }

    private IEnumerable<IMessage> ProcessConversationsForRolePlay(IEnumerable<IMessage> messages)
    {
        return messages.Select((x, i) =>
        {
            var msg = @$"From {x.From}:
{x.GetContent()}
<eof_msg>
round # {i}";

            return new TextMessage(Role.User, content: msg);
        });
    }
}
