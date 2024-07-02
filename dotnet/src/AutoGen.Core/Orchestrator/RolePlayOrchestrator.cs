// Copyright (c) Microsoft Corporation. All rights reserved.
// RolePlayOrchestrator.cs

using System;
using System.Collections.Generic;
using System.Linq;
using System.Runtime.CompilerServices;
using System.Threading;

namespace AutoGen.Core;

public class RolePlayOrchestrator : IOrchestrator
{
    private readonly IAgent admin;
    private readonly Graph? workflow = null;
    public RolePlayOrchestrator(IAgent admin, Graph? workflow = null)
    {
        this.admin = admin;
        this.workflow = workflow;
    }

    public async IAsyncEnumerable<IAgent> GetNextSpeakerAsync(
        OrchestrationContext context,
        int maxRound,
        [EnumeratorCancellation] CancellationToken cancellationToken = default)
    {
        var lastMessage = context.ChatHistory.LastOrDefault();
        if (lastMessage == null)
        {
            yield break;
        }

        var candidates = context.Candidates.ToList();
        var currentSpeaker = candidates.First(candidates => candidates.Name == lastMessage.From);

        // if there's a workflow
        // and the next available agent from the workflow is in the group chat
        // then return the next agent from the workflow
        if (this.workflow != null)
        {
            var nextAgents = await this.workflow.TransitToNextAvailableAgentsAsync(currentSpeaker, context.ChatHistory);
            nextAgents = nextAgents.Where(nextAgent => candidates.Any(candidate => candidate.Name == nextAgent.Name));
            candidates = nextAgents.ToList();
            if (!candidates.Any())
            {
                yield break;
            }

            if (candidates is { Count: 1 })
            {
                yield return nextAgents.First();
            }
        }

        // In this case, since there are more than one available agents from the workflow for the next speaker
        // the admin will be invoked to decide the next speaker
        var agentNames = candidates.Select(candidate => candidate.Name);
        var systemMessage = new TextMessage(Role.System,
            content: $@"You are in a role play game. Carefully read the conversation history and carry on the conversation.
The available roles are:
{string.Join(",", agentNames)}

Each message will start with 'From name:', e.g:
From {agentNames.First()}:
//your message//.");

        var chatHistoryWithName = this.ProcessConversationsForRolePlay(context.ChatHistory);
        var messages = new IMessage[] { systemMessage }.Concat(chatHistoryWithName);

        var response = await this.admin.GenerateReplyAsync(
            messages: messages,
            options: new GenerateReplyOptions
            {
                Temperature = 0,
                MaxToken = 128,
                StopSequence = [":"],
                Functions = [],
            });

        var name = response?.GetContent() ?? throw new Exception("No name is returned.");

        // remove From
        name = name!.Substring(5);
        var candidate = candidates.FirstOrDefault(x => x.Name!.ToLower() == name.ToLower());

        if (candidate != null)
        {
            yield return candidate;
        }

        yield break;
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
