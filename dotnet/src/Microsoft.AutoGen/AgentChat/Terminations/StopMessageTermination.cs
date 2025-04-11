using Microsoft.AutoGen.AgentChat.Abstractions;

namespace Microsoft.AutoGen.AgentChat.Terminations;

/// <summary>
/// Terminate a conversation if a <see cref="StopMessage"/> is received.
/// </summary>
public class StopMessageTermination : ITerminationCondition
{
    public bool IsTerminated { get; private set; }

    public ValueTask<StopMessage?> CheckAndUpdateAsync(IList<AgentMessage> messages)
    {
        if (this.IsTerminated)
        {
            throw new TerminatedException();
        }

        foreach (AgentMessage item in messages)
        {
            if (item is StopMessage)
            {
                this.IsTerminated = true;

                StopMessage result = new() { Content = "Stop message received", Source = nameof(StopMessageTermination) };
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
