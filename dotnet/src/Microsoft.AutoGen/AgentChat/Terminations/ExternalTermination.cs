// Copyright (c) Microsoft Corporation. All rights reserved.
// ExternalTermination.cs

using Microsoft.AutoGen.AgentChat.Abstractions;

namespace Microsoft.AutoGen.AgentChat.Terminations;

/// <summary>
/// A <see cref="ITerminationCondition"/> that is externally controlled by calling the <see cref="Set"/> method.
/// </summary>
public sealed class ExternalTermination : ITerminationCondition
{
    public ExternalTermination()
    {
        this.TerminationQueued = false;
        this.IsTerminated = false;
    }

    public bool TerminationQueued { get; private set; }
    public bool IsTerminated { get; private set; }

    /// <summary>
    /// Set the termination condition to terminated.
    /// </summary>
    public void Set()
    {
        this.TerminationQueued = true;
    }

    public ValueTask<StopMessage?> CheckAndUpdateAsync(IList<AgentMessage> messages)
    {
        if (this.IsTerminated)
        {
            throw new TerminatedException();
        }

        if (this.TerminationQueued)
        {
            this.IsTerminated = true;
            string message = "External termination requested.";
            StopMessage result = new() { Content = message, Source = nameof(ExternalTermination) };
            return ValueTask.FromResult<StopMessage?>(result);
        }

        return ValueTask.FromResult<StopMessage?>(null);
    }

    public void Reset()
    {
        this.TerminationQueued = false;
        this.IsTerminated = false;
    }
}
