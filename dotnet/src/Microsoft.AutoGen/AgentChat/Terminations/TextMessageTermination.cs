// Copyright (c) Microsoft Corporation. All rights reserved.
// TextMessageTermination.cs

using Microsoft.AutoGen.AgentChat.Abstractions;

namespace Microsoft.AutoGen.AgentChat.Terminations;

/// <summary>
/// Terminate the conversation if a <see cref="TextMessage"/> is received.
///
/// This termination condition checks for TextMessage instances in the message sequence. When a TextMessage is found,
/// it terminates the conversation if either:
/// 
/// <list type="bullet">
///     <item>No source was specified (terminates on any <see cref="TextMessage"/>)</item>
///     <item>The message source matches the specified source</item>
/// </list>
/// 
/// </summary>
public sealed class TextMessageTermination : ITerminationCondition
{
    /// <summary>
    /// Initializes a new instance of the <see cref="TextMessageTermination"/> class.
    /// </summary>
    /// <param name="source">
    /// The source name to match against incoming messages. If <c>null</c>, matches any source.
    /// Defaults to <c>null</c>.
    /// </param>
    public TextMessageTermination(string? source = null)
    {
        this.Source = source;
        this.IsTerminated = false;
    }

    public string? Source { get; }
    public bool IsTerminated { get; private set; }

    public ValueTask<StopMessage?> CheckAndUpdateAsync(IList<AgentMessage> messages)
    {
        if (this.IsTerminated)
        {
            throw new TerminatedException();
        }

        foreach (AgentMessage item in messages)
        {
            if (item is TextMessage textMessage && (this.Source == null || textMessage.Source == this.Source))
            {
                this.IsTerminated = true;
                string message = $"Text message received from '{textMessage.Source}'.";
                StopMessage result = new() { Content = message, Source = nameof(TextMessageTermination) };
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
