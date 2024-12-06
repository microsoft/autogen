// Copyright (c) Microsoft Corporation. All rights reserved.
// Termination.cs

namespace Microsoft.AutoGen.AgentChat.Abstractions;

public interface ITerminationCondition
{
    /// <summary>
    /// Checkes if the termination condition has been reached
    /// </summary>
    bool IsTerminated { get; }

    /// <summary>
    /// Check if the conversation should be terminated based on the messages received
    /// since the last time the condition was called.
    /// Return a <see cref="StopMessage"/> if the conversation should be terminated, or <c>null</c> otherwise.
    /// </summary>
    /// <param name="messages">The messages received since the last time the condition was called.</param>
    /// <returns>A <see cref="StopMessage"/> if the conversation should be terminated, or <c>null</c>
    /// otherwise.</returns>
    /// <exception cref="TerminatedException">If the termination condition has already been reached.</exception>
    ValueTask<StopMessage?> UpdateAsync(IList<AgentMessage> messages);

    /// <summary>
    /// Resets the termination condition.
    /// </summary>
    void Reset();

    ITerminationCondition Or(ITerminationCondition other)
    {
        return new CombinerCondition(CombinerCondition.Or, this, other);
    }

    ITerminationCondition And(ITerminationCondition other)
    {
        return new CombinerCondition(CombinerCondition.And, this, other);
    }
}

public sealed class TerminatedException : Exception
{
    public TerminatedException() : base("The termination condition has already been reached.")
    {
    }
}

internal sealed class CombinerCondition : ITerminationCondition
{
    public const bool Conjunction = true;
    public const bool Disjunction = false;

    public const bool And = Conjunction;
    public const bool Or = Disjunction;

    private List<StopMessage> stopMessages = new List<StopMessage>();
    private List<ITerminationCondition> clauses;
    private readonly bool conjunction;

    public CombinerCondition(bool conjuction, params IEnumerable<ITerminationCondition> clauses)
    {
        // Flatten the list of clauses by unwrapping included CombinerConditions if their
        // conjuctions match (since combiners with associative conjuctions can be hoisted).
        IEnumerable<ITerminationCondition> flattened =
            clauses.SelectMany(c =>
                    (c is CombinerCondition combiner && combiner.conjunction == conjuction)
                    ? (IEnumerable<ITerminationCondition>) combiner.clauses
                    : new[] { c });

        this.conjunction = conjuction;

        this.clauses = flattened.ToList();
    }

    public bool IsTerminated { get; private set; }

    public void Reset()
    {
        this.stopMessages.Clear();
        this.clauses.ForEach(c => c.Reset());

        this.IsTerminated = false;
    }

    public async ValueTask<StopMessage?> UpdateAsync(IList<AgentMessage> messages)
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
        List<Task<StopMessage?>> tasks = candidateTerminations.Select(c => c.UpdateAsync(messages).AsTask()).ToList();
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
                // If any clause does not terminate, the conjuction does not terminate
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
