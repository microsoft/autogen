// Copyright (c) Microsoft Corporation. All rights reserved.
// Graph.cs

using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;

namespace AutoGen.Core;

public class Graph
{
    private readonly List<Transition> transitions = new List<Transition>();

    public Graph()
    {
    }

    public Graph(IEnumerable<Transition>? transitions)
    {
        if (transitions != null)
        {
            this.transitions.AddRange(transitions);
        }
    }

    public void AddTransition(Transition transition)
    {
        transitions.Add(transition);
    }

    /// <summary>
    /// Get the transitions of the workflow.
    /// </summary>
    public IEnumerable<Transition> Transitions => transitions;

    /// <summary>
    /// Get the next available agents that the messages can be transit to.
    /// </summary>
    /// <param name="fromAgent">the from agent</param>
    /// <param name="messages">messages</param>
    /// <returns>A list of agents that the messages can be transit to</returns>
    public async Task<IEnumerable<IAgent>> TransitToNextAvailableAgentsAsync(IAgent fromAgent, IEnumerable<IMessage> messages)
    {
        var nextAgents = new List<IAgent>();
        var availableTransitions = transitions.FindAll(t => t.From == fromAgent) ?? Enumerable.Empty<Transition>();
        foreach (var transition in availableTransitions)
        {
            if (await transition.CanTransitionAsync(messages))
            {
                nextAgents.Add(transition.To);
            }
        }

        return nextAgents;
    }
}

/// <summary>
/// Represents a transition between two agents.
/// </summary>
public class Transition
{
    private readonly IAgent _from;
    private readonly IAgent _to;
    private readonly Func<IAgent, IAgent, IEnumerable<IMessage>, Task<bool>>? _canTransition;

    /// <summary>
    /// Create a new instance of <see cref="Transition"/>.
    /// This constructor is used for testing purpose only.
    /// To create a new instance of <see cref="Transition"/>, use <see cref="Transition.Create{TFromAgent, TToAgent}(TFromAgent, TToAgent, Func{TFromAgent, TToAgent, IEnumerable{IMessage}, Task{bool}}?)"/>.
    /// </summary>
    /// <param name="from">from agent</param>
    /// <param name="to">to agent</param>
    /// <param name="canTransitionAsync">detect if the transition is allowed, default to be always true</param>
    internal Transition(IAgent from, IAgent to, Func<IAgent, IAgent, IEnumerable<IMessage>, Task<bool>>? canTransitionAsync = null)
    {
        _from = from;
        _to = to;
        _canTransition = canTransitionAsync;
    }

    /// <summary>
    /// Create a new instance of <see cref="Transition"/>.
    /// </summary>
    /// <returns><see cref="Transition"/></returns>"
    public static Transition Create<TFromAgent, TToAgent>(TFromAgent from, TToAgent to, Func<TFromAgent, TToAgent, IEnumerable<IMessage>, Task<bool>>? canTransitionAsync = null)
        where TFromAgent : IAgent
        where TToAgent : IAgent
    {
        return new Transition(from, to, (fromAgent, toAgent, messages) => canTransitionAsync?.Invoke((TFromAgent)fromAgent, (TToAgent)toAgent, messages) ?? Task.FromResult(true));
    }

    public IAgent From => _from;

    public IAgent To => _to;

    /// <summary>
    /// Check if the transition is allowed.
    /// </summary>
    /// <param name="messages">messages</param>
    public Task<bool> CanTransitionAsync(IEnumerable<IMessage> messages)
    {
        if (_canTransition == null)
        {
            return Task.FromResult(true);
        }

        return _canTransition(this.From, this.To, messages);
    }
}
