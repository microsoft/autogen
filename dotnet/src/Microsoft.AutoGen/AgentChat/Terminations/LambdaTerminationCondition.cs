// Copyright (c) Microsoft Corporation. All rights reserved.
// LambdaTerminationCondition.cs
using Microsoft.AutoGen.AgentChat.Abstractions;

namespace Microsoft.AutoGen.AgentChat.Terminations;

/// <summary>
/// A termination condition that evaluates a lambda function against the latest ChatMessage.
/// </summary>
public sealed class LambdaTerminationCondition : ITerminationCondition
{
    private readonly Func<ChatMessage, bool> _condition;
    public bool IsTerminated { get; private set; }

    /// <summary>
    /// Initializes a new instance of the <see cref="LambdaTerminationCondition"/> class.
    /// </summary>
    /// <param name="condition">A lambda function that takes a <see cref="ChatMessage"/> and returns a boolean indicating if the termination condition is met.</param>
    public LambdaTerminationCondition(Func<ChatMessage, bool> condition)
    {
        _condition = condition ?? throw new ArgumentNullException(nameof(condition));
        IsTerminated = false;
    }

    public ValueTask<StopMessage?> CheckAndUpdateAsync(IList<AgentMessage> messages)
    {
        if (IsTerminated)
        {
            throw new TerminatedException();
        }

        // Find the latest ChatMessage
        for (int i = messages.Count - 1; i >= 0; i--)
        {
            if (messages[i] is ChatMessage chatMsg && _condition(chatMsg))
            {
                IsTerminated = true;
                return ValueTask.FromResult<StopMessage?>(new StopMessage { Content = "Lambda termination condition met.", Source = nameof(LambdaTerminationCondition) });
            }
        }
        return ValueTask.FromResult<StopMessage?>(null);
    }

    public void Reset() => IsTerminated = false;
}
