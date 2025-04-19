using Microsoft.AutoGen.AgentChat.Abstractions;

namespace Microsoft.AutoGen.AgentChat.Terminations;

/// <summary>
/// Terminate the conversation if the token usage limit is reached.
/// </summary>
public sealed class TokenUsageTermination : ITerminationCondition
{
    /// <summary>
    /// Initializes a new instance of the <see cref="TokenUsageTermination"/> class.
    /// </summary>
    /// <param name="maxTotalTokens">The maximum total number of tokens allowed in the conversation.</param>
    /// <param name="maxPromptTokens">The maximum number of prompt tokens allowed in the conversation.</param>
    /// <param name="maxCompletionTokens">The maximum number of completion tokens allowed in the conversation.</param>
    public TokenUsageTermination(int? maxTotalTokens = null, int? maxPromptTokens = null, int? maxCompletionTokens = null)
    {
        this.MaxTotalTokens = maxTotalTokens;
        this.MaxPromptTokens = maxPromptTokens;
        this.MaxCompletionTokens = maxCompletionTokens;

        this.PromptTokenCount = 0;
        this.CompletionTokenCount = 0;
    }

    public int? MaxTotalTokens { get; }
    public int? MaxPromptTokens { get; }
    public int? MaxCompletionTokens { get; }

    public int TotalTokenCount => this.PromptTokenCount + this.CompletionTokenCount;
    public int PromptTokenCount { get; private set; }
    public int CompletionTokenCount { get; private set; }

    public bool IsTerminated =>
        (this.MaxTotalTokens != null && this.TotalTokenCount >= this.MaxTotalTokens) ||
        (this.MaxPromptTokens != null && this.PromptTokenCount >= this.MaxPromptTokens) ||
        (this.MaxCompletionTokens != null && this.CompletionTokenCount >= this.MaxCompletionTokens);

    public ValueTask<StopMessage?> CheckAndUpdateAsync(IList<AgentMessage> messages)
    {
        if (this.IsTerminated)
        {
            throw new TerminatedException();
        }

        foreach (AgentMessage item in messages)
        {
            if (item.ModelUsage is RequestUsage usage)
            {
                this.PromptTokenCount += usage.PromptTokens;
                this.CompletionTokenCount += usage.CompletionTokens;
            }
        }

        if (this.IsTerminated)
        {
            string message = $"Token usage limit reached, total token count: {this.TotalTokenCount}, prompt token count: {this.PromptTokenCount}, completion token count: {this.CompletionTokenCount}.";
            StopMessage result = new() { Content = message, Source = nameof(TokenUsageTermination) };
            return ValueTask.FromResult<StopMessage?>(result);
        }

        return ValueTask.FromResult<StopMessage?>(null);
    }

    public void Reset()
    {
        this.PromptTokenCount = 0;
        this.CompletionTokenCount = 0;
    }
}
