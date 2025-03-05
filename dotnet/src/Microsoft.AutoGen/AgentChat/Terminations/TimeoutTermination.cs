// Copyright (c) Microsoft Corporation. All rights reserved.
// TimeoutTermination.cs

using Microsoft.AutoGen.AgentChat.Abstractions;

namespace Microsoft.AutoGen.AgentChat.Terminations;

/// <summary>
/// Terminate the conversation after the specified duration has passed.
/// </summary>
public sealed class TimeoutTermination : ITerminationCondition
{
    /// <summary>
    /// Initializes a new instance of the <see cref="TimeoutTermination"/> class.
    /// </summary>
    /// <param name="timeout">The maximum duration before terminating the conversation.</param>
    public TimeoutTermination(TimeSpan timeout)
    {
        this.Timeout = timeout;
        this.StartTime = DateTime.UtcNow;
    }

    /// <summary>
    /// Initializes a new instance of the <see cref="TimeoutTermination"/> class.
    /// </summary>
    /// <param name="seconds">The maximum duration in seconds before terminating the conversation.</param>
    public TimeoutTermination(float seconds) : this(TimeSpan.FromSeconds(seconds))
    {
    }

    public TimeSpan Timeout { get; }
    public DateTime StartTime { get; private set; }

    public bool IsTerminated { get; private set; }

    public ValueTask<StopMessage?> CheckAndUpdateAsync(IList<AgentMessage> messages)
    {
        if (this.IsTerminated)
        {
            throw new TerminatedException();
        }

        if (DateTime.UtcNow - this.StartTime >= this.Timeout)
        {
            this.IsTerminated = true;
            string message = $"Timeout of {this.Timeout.TotalSeconds} seconds reached.";
            StopMessage result = new() { Content = message, Source = nameof(TimeoutTermination) };
            return ValueTask.FromResult<StopMessage?>(result);
        }

        return ValueTask.FromResult<StopMessage?>(null);
    }

    public void Reset()
    {
        this.IsTerminated = false;
        this.StartTime = DateTime.UtcNow;
    }
}
