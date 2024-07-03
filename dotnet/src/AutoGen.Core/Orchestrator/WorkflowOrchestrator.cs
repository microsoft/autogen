// Copyright (c) Microsoft Corporation. All rights reserved.
// WorkflowOrchestrator.cs

using System.Collections.Generic;
using System.Linq;
using System.Runtime.CompilerServices;
using System.Threading;

namespace AutoGen.Core;

public class WorkflowOrchestrator : IOrchestrator
{
    private readonly Graph workflow;

    public WorkflowOrchestrator(Graph workflow)
    {
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
        var currentSpeaker = candidates.FirstOrDefault(candidates => candidates.Name == lastMessage.From);

        if (currentSpeaker == null)
        {
            yield break;
        }
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
        else
        {
            throw new System.Exception("There are more than one available agents from the workflow for the next speaker.");
        }
    }
}
