// Copyright (c) Microsoft Corporation. All rights reserved.
// Termination.cs

namespace Microsoft.AutoGen.AgentChat.Abstractions;

public static class TerminationConditionExtensions
{
    /// <summary>
    /// Combine this termination condition with another using a logical OR.
    /// </summary>
    /// <param name="other">Another termination condition.</param>
    /// <returns>The combined termination condition, with appropriate short-circuiting.</returns>
    public static ITerminationCondition Or(this ITerminationCondition this_, ITerminationCondition other)
    {
        return new CombinerCondition(CombinerCondition.Or, this_, other);
    }

    /// <summary>
    /// Combine this termination condition with another using a logical AND.
    /// </summary>
    /// <param name="other">Another termination condition.</param>
    /// <returns>The combined termination condition, with appropriate short-circuiting.</returns>
    public static ITerminationCondition And(this ITerminationCondition this_, ITerminationCondition other)
    {
        return new CombinerCondition(CombinerCondition.And, this_, other);
    }
}

/// <summary>
/// A stateful condition that determines when a conversation should be terminated.
///
/// A termination condition takes a sequences of <see cref="AgentMessage"/> objects since the last time the
/// condition was checked, and returns a <see cref="StopMessage"/> if the conversation should be terminated,
/// or <c>null</c> otherwise.
///
/// Once a termination condition has been reached, it must be <see cref="Reset()"/> before it can be used again.
///
/// Termination conditions can be combined using the <see cref="TerminationConditionExtensions.Or"/> and
/// <see cref="TerminationConditionExtensions.And"/> methods.
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
    /// Combine two termination conditions with another using an associative, short-circuiting OR.
    /// </summary>
    /// <param name="left">
    /// The left-hand side termination condition. If this condition is already a disjunction, the RHS condition is added to the list of clauses.
    /// </param>
    /// <param name="right">
    /// The right-hand side termination condition. If the LHS condition is already a disjunction, this condition is added to the list of clauses.
    /// </param>
    /// <returns>
    /// The combined termination condition, with appropriate short-circuiting.
    /// </returns>
    public static ITerminationCondition operator |(ITerminationCondition left, ITerminationCondition right)
    {
        return left.Or(right);
    }

    /// <summary>
    /// Combine two termination conditions with another using an associative, short-circuiting AND.
    /// </summary>
    /// <param name="left">
    /// The left-hand side termination condition. If this condition is already a conjunction, the RHS condition is added to the list of clauses.
    /// </param>
    /// <param name="right">
    /// The right-hand side termination condition. If the LHS condition is already a conjunction, this condition is added to the list of clauses.
    /// </param>
    /// <returns>
    /// The combined termination condition, with appropriate short-circuiting.
    /// </returns>
    public static ITerminationCondition operator &(ITerminationCondition left, ITerminationCondition right)
    {
        return left.And(right);
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
}
