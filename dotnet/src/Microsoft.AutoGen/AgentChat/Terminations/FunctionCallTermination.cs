using Microsoft.AutoGen.AgentChat.Abstractions;

namespace Microsoft.AutoGen.AgentChat.Terminations;

/// <summary>
/// Terminate the conversation if a <see cref="ToolCallExecutionEvent"/> with a specific name is received.
/// </summary>
public sealed class FunctionCallTermination : ITerminationCondition
{
    /// <summary>
    /// Initializes a new instance of the <see cref="FunctionCallTermination"/> class.
    /// </summary>
    /// <param name="functionName">The name of the function to look for in the messages.</param>
    public FunctionCallTermination(string functionName)
    {
        this.FunctionName = functionName;
        this.IsTerminated = false;
    }

    public string FunctionName { get; }
    public bool IsTerminated { get; private set; }

    public ValueTask<StopMessage?> CheckAndUpdateAsync(IList<AgentMessage> messages)
    {
        if (this.IsTerminated)
        {
            throw new TerminatedException();
        }

        foreach (AgentMessage item in messages)
        {
            if (item is ToolCallExecutionEvent toolCallEvent && toolCallEvent.Content.Any(execution => execution.Name == this.FunctionName))
            {
                this.IsTerminated = true;
                string message = $"Function '{this.FunctionName}' was executed.";
                StopMessage result = new() { Content = message, Source = nameof(FunctionCallTermination) };
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
