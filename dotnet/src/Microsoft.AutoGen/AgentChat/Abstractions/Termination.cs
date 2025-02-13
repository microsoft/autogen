// Copyright (c) Microsoft Corporation. All rights reserved.
// Termination.cs

namespace Microsoft.AutoGen.AgentChat.Abstractions;

/// <summary>
/// A stateful condition that determines when a conversation should be terminated.
///
/// A termination condition takes a sequences of <see cref="AgentMessage"/> objects since the last time the
/// condition was checked, and returns a <see cref="StopMessage"/> if the conversation should be terminated,
/// or <c>null</c> otherwise.
///
/// Once a termination condition has been reached, it must be <see cref="Reset()"/> before it can be used again.
///
/// Termination conditions can be combined using the <see cref="Or"/> and <see cref="And"/> methods.
/// </summary>
public interface ITerminationCondition
{
    /// <summary>
    /// Checks if the termination condition has been reached
    /// </summary>
    public bool IsTerminated { get; }

    /// <summary>
    /// Check if the conversation should be terminated based on the messages received
    /// since the last time the condition was called.
    /// Return a <see cref="StopMessage"/> if the conversation should be terminated, or <c>null</c> otherwise.
    /// </summary>
    /// <param name="messages">The messages received since the last time the condition was called.</param>
    /// <returns>A <see cref="StopMessage"/> if the conversation should be terminated, or <c>null</c>
    /// otherwise.</returns>
    /// <exception cref="TerminatedException">If the termination condition has already been reached.</exception>
    public ValueTask<StopMessage?> CheckAndUpdateAsync(IList<AgentMessage> messages);

    /// <summary>
    /// Resets the termination condition.
    /// </summary>
    public void Reset();

    /// <summary>
    /// Combine this termination condition with another using a logical OR.
    /// </summary>
    /// <param name="other">Another termination condition.</param>
    /// <returns>The combined termination condition, with appropriate short-circuiting.</returns>
    public ITerminationCondition Or(ITerminationCondition other)
    {
        return new CombinerCondition(CombinerCondition.Or, this, other);
    }

    /// <summary>
    /// Combine this termination condition with another using a logical AND.
    /// </summary>
    /// <param name="other">Another termination condition.</param>
    /// <returns>The combined termination condition, with appropriate short-circuiting.</returns>
    public ITerminationCondition And(ITerminationCondition other)
    {
        return new CombinerCondition(CombinerCondition.And, this, other);
    }
}

/// <summary>
/// Exception thrown when a termination condition has already been reached.
/// </summary>
public sealed class TerminatedException : Exception
{
    public TerminatedException() : base("The termination condition has already been reached.")
    {
    }
}

/// <summary>
/// A termination condition that combines multiple termination conditions using a logical AND or OR.
/// </summary>
internal sealed class CombinerCondition : ITerminationCondition
{
    public const bool Conjunction = true;
    public const bool Disjunction = false;

    public const bool And = Conjunction;
    public const bool Or = Disjunction;

    private List<StopMessage> stopMessages = new List<StopMessage>();
    private List<ITerminationCondition> clauses;
    private readonly bool conjunction;

    /// <summary>
    /// Create a new <see cref="CombinerCondition"/> with the given conjunction and clauses.
    /// </summary>
    /// <param name="conjunction">The conjunction to use when combining the clauses.</param>
    /// <param name="clauses">The termination conditions to combine.</param>
    public CombinerCondition(bool conjunction, params IEnumerable<ITerminationCondition> clauses)
    {
        // Flatten the list of clauses by unwrapping included CombinerConditions if their
        // conjunctions match (since combiners with associative conjunctions can be hoisted).
        IEnumerable<ITerminationCondition> flattened =
            clauses.SelectMany(c =>
                    (c is CombinerCondition combiner && combiner.conjunction == conjunction)
                    ? (IEnumerable<ITerminationCondition>)combiner.clauses
                    : new[] { c });

        this.conjunction = conjunction;

        this.clauses = flattened.ToList();
    }

    /// <inheritdoc cref="ITerminationCondition.IsTerminated" />
    public bool IsTerminated { get; private set; }

    /// <inheritdoc cref="ITerminationCondition.Reset" />
    public void Reset()
    {
        this.stopMessages.Clear();
        this.clauses.ForEach(c => c.Reset());

        this.IsTerminated = false;
    }

    /// <inheritdoc cref="ITerminationCondition.CheckAndUpdateAsync" />
    public async ValueTask<StopMessage?> CheckAndUpdateAsync(IList<AgentMessage> messages)
    {
        if (this.IsTerminated)
        {
            throw new TerminatedException();
        }

        // When operating as a conjunction, we may be accumulated terminating conditions, but we will not fire until
        // all of them are complete. In this case, we need to avoid continuing to interact with already terminated
        // clauses, because trying to update them will throw
        var candidateTerminations = this.conjunction ? this.clauses.Where(clause => !clause.IsTerminated) : clauses;

        // TODO: Do we really need these to be ValueTasks? (Alternatively: Do we really need to run them explicitly
        // on every invocation, or is a Worker pattern more appropriate?)
        List<Task<StopMessage?>> tasks = candidateTerminations.Select(c => c.CheckAndUpdateAsync(messages).AsTask()).ToList();
        StopMessage?[] results = await Task.WhenAll(tasks);

        bool raiseTermination = this.conjunction; // if or, we start with false until we observe a true
                                                  // if and, we start with true until we observe a false

        foreach (StopMessage? maybeStop in results)
        {
            if (maybeStop != null)
            {
                this.stopMessages.Add(maybeStop);
                if (!this.conjunction)
                {
                    // If any clause terminates, the disjunction terminates
                    raiseTermination = true;
                }
            }
            else if (this.conjunction)
            {
                // If any clause does not terminate, the conjunction does not terminate
                raiseTermination = false;
            }
        }

        if (raiseTermination)
        {
            this.IsTerminated = true;

            return new StopMessage
            {
                Content = string.Join("; ", stopMessages.Select(sm => sm.Content)),
                Source = string.Join(", ", stopMessages.Select(sm => sm.Source))
            };
        }

        return null;
    }

    /// <inheritdoc cref="ITerminationCondition.Or" />
    /// <remarks>
    /// If this condition is already a disjunction, the new condition is added to the list of clauses.
    /// </remarks>
    ITerminationCondition ITerminationCondition.Or(ITerminationCondition other)
    {
        if (this.conjunction == Or)
        {
            this.clauses.Add(other);
            return this;
        }
        else
        {
            return new CombinerCondition(Or, this, new CombinerCondition(Or, other));
        }
    }

    /// <inheritdoc cref="ITerminationCondition.And" />
    /// <remarks>
    /// If this condition is already a conjunction, the new condition is added to the list of clauses.
    /// </remarks>
    ITerminationCondition ITerminationCondition.And(ITerminationCondition other)
    {
        if (this.conjunction == And)
        {
            this.clauses.Add(other);
            return this;
        }
        else
        {
            return new CombinerCondition(And, this, new CombinerCondition(And, other));
        }
    }
}
