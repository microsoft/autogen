using Microsoft.AutoGen.AgentChat.Abstractions;
using Microsoft.Extensions.AI;

namespace Microsoft.AutoGen.AgentChat.Terminations;

/// <summary>
/// Terminate the conversation if a specific text is mentioned.
/// </summary>
public sealed class TextMentionTermination : ITerminationCondition
{
    /// <summary>
    /// Initializes a new instance of the <see cref="TextMentionTermination"/> class.
    /// </summary>
    /// <param name="targetText">The text to look for in the messages.</param>
    /// <param name="sources">Check only the messages of the specified agents for the text to look for.</param>
    public TextMentionTermination(string targetText, IEnumerable<string>? sources = null)
    {
        this.TargetText = targetText;
        this.Sources = sources != null ? [.. sources] : null;
        this.IsTerminated = false;
    }

    public string TargetText { get; }
    public HashSet<string>? Sources { get; }

    public bool IsTerminated { get; private set; }

    private bool CheckMultiModalData(MultiModalData data)
    {
        return data.ContentType == MultiModalData.Type.String &&
               ((TextContent)data.AIContent).Text.Contains(this.TargetText);
    }

    public ValueTask<StopMessage?> CheckAndUpdateAsync(IList<AgentMessage> messages)
    {
        if (this.IsTerminated)
        {
            throw new TerminatedException();
        }

        foreach (AgentMessage item in messages)
        {
            if (this.Sources != null && !this.Sources.Contains(item.Source))
            {
                continue;
            }

            bool hasMentions = item switch
            {
                TextMessage textMessage => textMessage.Content.Contains(this.TargetText),
                MultiModalMessage multiModalMessage => multiModalMessage.Content.Any(CheckMultiModalData),
                StopMessage stopMessage => stopMessage.Content.Contains(this.TargetText),
                ToolCallSummaryMessage toolCallSummaryMessage => toolCallSummaryMessage.Content.Contains(this.TargetText),

                _ => false
            };

            if (hasMentions)
            {
                this.IsTerminated = true;
                StopMessage result = new() { Content = "Text mention received", Source = nameof(TextMentionTermination) };
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
