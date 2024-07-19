// Copyright (c) Microsoft Corporation. All rights reserved.
// RoundRobinOrchestrator.cs

using System.Linq;
using System.Threading;
using System.Threading.Tasks;

namespace AutoGen.Core;

/// <summary>
/// Return the next agent in a round-robin fashion.
/// <para>
/// If the last message is from one of the candidates, the next agent will be the next candidate in the list.
/// </para>
/// <para>
/// Otherwise, no agent will be selected. In this case, the orchestrator will return an empty list.
/// </para>
/// <para>
/// This orchestrator always return a single agent.
/// </para>
/// </summary>
public class RoundRobinOrchestrator : IOrchestrator
{
    public async Task<IAgent?> GetNextSpeakerAsync(
        OrchestrationContext context,
        CancellationToken cancellationToken = default)
    {
        var lastMessage = context.ChatHistory.LastOrDefault();

        if (lastMessage == null)
        {
            return null;
        }

        var candidates = context.Candidates.ToList();
        var lastAgentIndex = candidates.FindIndex(a => a.Name == lastMessage.From);
        if (lastAgentIndex == -1)
        {
            return null;
        }

        var nextAgentIndex = (lastAgentIndex + 1) % candidates.Count;
        return candidates[nextAgentIndex];
    }
}
