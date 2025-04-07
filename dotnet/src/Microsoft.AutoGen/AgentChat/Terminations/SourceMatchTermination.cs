// Copyright (c) Microsoft Corporation. All rights reserved.
// SourceMatchTermination.cs

using Microsoft.AutoGen.AgentChat.Abstractions;

namespace Microsoft.AutoGen.AgentChat.Terminations;

/// <summary>
/// Terminate the conversation after a specific source responds.
/// </summary>
public sealed class SourceMatchTermination : ITerminationCondition
{
    /// <summary>
    /// Initializes a new instance of the <see cref="SourceMatchTermination"/> class.
    /// </summary>
    /// <param name="sources">List of source names to terminate the conversation.</param>
    public SourceMatchTermination(params IEnumerable<string> sources)
    {
        this.Sources = [.. sources];
    }

    public HashSet<string> Sources { get; }
    public bool IsTerminated { get; private set; }

    public ValueTask<StopMessage?> CheckAndUpdateAsync(IList<AgentMessage> messages)
    {
        if (this.IsTerminated)
        {
            throw new TerminatedException();
        }

        foreach (AgentMessage item in messages)
        {
            if (this.Sources.Contains(item.Source))
            {
                this.IsTerminated = true;
                string message = $"'{item.Source}' answered.";
                StopMessage result = new() { Content = message, Source = nameof(SourceMatchTermination) };
                return ValueTask.FromResult<StopMessage?>(result);
            }
        }

        return ValueTask.FromResult<StopMessage?>(null);
    }

    public void Reset()
    {
        this.IsTerminated = false;
    }
}
