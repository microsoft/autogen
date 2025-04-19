using Microsoft.AutoGen.AgentChat.Abstractions;

namespace Microsoft.AutoGen.AgentChat.Terminations;

/// <summary>
/// Terminate the conversation if a <see cref="HandoffMessage"/> with the given <see cref="HandoffMessage.Target"/>
/// is received.
/// </summary>
public sealed class HandoffTermination : ITerminationCondition
{
    /// <summary>
    /// Initializes a new instance of the <see cref="HandoffTermination"/> class.
    /// </summary>
    /// <param name="target">The target of the handoff message.</param>
    public HandoffTermination(string target)
    {
        this.Target = target;
        this.IsTerminated = false;
    }

    public string Target { get; }
    public bool IsTerminated { get; private set; }

    public ValueTask<StopMessage?> CheckAndUpdateAsync(IList<AgentMessage> messages)
    {
        if (this.IsTerminated)
        {
            throw new TerminatedException();
        }

        foreach (AgentMessage item in messages)
        {
            if (item is HandoffMessage handoffMessage && handoffMessage.Target == this.Target)
            {
                this.IsTerminated = true;

                string message = $"Handoff to {handoffMessage.Target} from {handoffMessage.Source} detected.";
                StopMessage result = new() { Content = message, Source = nameof(HandoffTermination) };
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
