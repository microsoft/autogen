// Copyright (c) Microsoft Corporation. All rights reserved.
// RolePlayOrchestrator.cs

using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;
using AutoGen.Core.Orchestrator;

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

## Available Speaker Names
{string.Join($"{Environment.NewLine}", agentNames.Select(z => $"- {z}"))}

## Output Role
Each message will use the strickly JSON format with a '//finish' suffix:
{{""Speaker"":""<From Speaker Name>"", ""Message"":""<Chat Message>""}}//finish

e,g:
{{""Speaker"":""{agentNames.First()}"", ""Message"":""Hi, I'm {agentNames.First()}.""}}//finish

Note:
1. ""Speaker"" must be one of the most suitable names in ""Available Speaker names"". You cannot create it yourself, nor can you merge two names, it must be 100% exactly equal. 
2. You have to output clean JSON result, no other words are allowed.");

        var chatHistoryWithName = this.ProcessConversationsForRolePlay(context.ChatHistory);
        var messages = new IMessage[] { rolePlayMessage }.Concat(chatHistoryWithName);

        var response = await this.admin.GenerateReplyAsync(
            messages: messages,
            options: new GenerateReplyOptions
            {
                Temperature = 0,
                MaxToken = 128,
                StopSequence = ["finish"],
                Functions = null,
            },
            cancellationToken: cancellationToken);

        var responseMessageStr = response.GetContent() ?? throw new ArgumentException("No name is returned.");

        RolePlayOrchestratorResponse? responseMessage;
        try
        {
            responseMessage = JsonSerializer.Deserialize<RolePlayOrchestratorResponse>(responseMessageStr);
            if (responseMessage == null)
            {
                throw new Exception("Incorrect RolePlayOrchestratorResponse JSON format.");
            }
        }
        catch
        {
            throw;
        }

        var name = responseMessage.Speaker;
        var candidate = candidates.FirstOrDefault(x => x.Name!.ToUpper() == name!.ToUpper());

        if (candidate != null)
        {
            return candidate;
        }

        //Regain the correct name
        var regainMessage = new TextMessage(Role.User,
            content: @$"Choose a name that is closest to the meaning from ""Available Speaker Names"" by ""Input Name"".

## Example
### Available Speaker Names
- Sales Manager
- General Manager Assistant
- Chief Financial Officer

### Input Name
CFO

### Outout Name
{{""Speaker"":""Chief Financial Officer"", ""Message"":""""}}//finish

## Task

Output Name must be one of the name in the following ""Available Speaker Names"" without any change.

Note:
1. ""Speaker"" must be one of the most suitable names in ""Available Speaker Names"". You cannot create it yourself, nor can you merge two names, it must be 100% exactly equal. 
2. You have to output clean JSON result,no other words are allowed.

### Speaker List
{string.Join($"{Environment.NewLine}", agentNames.Select(z => $"- {z}"))}

### Input Name
{name}

### Output Name");

        var regainResponse = await this.admin.GenerateReplyAsync(
            messages: new[] { regainMessage },
            options: new GenerateReplyOptions
            {
                Temperature = 0,
                MaxToken = 1024,
                StopSequence = ["//finish"],
                Functions = null,
            },
            cancellationToken: cancellationToken);

        RolePlayOrchestratorResponse? regainResponseMessage;
        var regainNameStr = regainResponse.GetContent() ?? throw new ArgumentException("No name is returned.");
        try
        {
            regainResponseMessage = JsonSerializer.Deserialize<RolePlayOrchestratorResponse>(regainNameStr);
            if (regainResponseMessage == null)
            {
                throw new Exception("Incorrect RolePlayOrchestratorResponse JSON format.");
            }
        }
        catch
        {
            throw;
        }

        var reaginCandidate = candidates.FirstOrDefault(x => x.Name!.ToUpper() == regainResponseMessage.Speaker!.ToUpper());

        if (reaginCandidate != null)
        {
            return reaginCandidate;
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
