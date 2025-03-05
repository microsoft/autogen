// Copyright (c) Microsoft Corporation. All rights reserved.
// MaxMessageTermination.cs

using Microsoft.AutoGen.AgentChat.Abstractions;

namespace Microsoft.AutoGen.AgentChat.Terminations;

/// <summary>
/// Terminate the conversation after a maximum number of messages have been exchanged.
/// </summary>
public sealed class MaxMessageTermination : ITerminationCondition
{
    /// <summary>
    /// Initializes a new instance of the <see cref="MaxMessageTermination"/> class.
    /// </summary>
    /// <param name="maxMessages">The maximum number of messages allowed in the conversation.</param>
    public MaxMessageTermination(int maxMessages)
    {
        this.MaxMessages = maxMessages;
        this.MessageCount = 0;
    }

    public int MaxMessages { get; }
    public int MessageCount { get; private set; }

    public bool IsTerminated => this.MessageCount >= this.MaxMessages;

    public ValueTask<StopMessage?> CheckAndUpdateAsync(IList<AgentMessage> messages)
    {
        if (this.IsTerminated)
        {
            throw new TerminatedException();
        }

        this.MessageCount += messages.Count;

        if (this.IsTerminated)
        {
            StopMessage result = new() { Content = "Max message count reached", Source = nameof(MaxMessageTermination) };
            return ValueTask.FromResult<StopMessage?>(result);
        }

        return ValueTask.FromResult<StopMessage?>(null);
    }

    public void Reset()
    {
        this.MessageCount = 0;
    }
}
