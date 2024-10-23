using Microsoft.Extensions.AI;
namespace Microsoft.AutoGen.Agents.Client;
public abstract class InferenceAgent<T> : AgentBase where T : class, new()
{
    protected IChatClient ChatClient { get; }
    public InferenceAgent(
        IAgentContext context,
        EventTypes typeRegistry, IChatClient client
        ) : base(context, typeRegistry)
    {
        ChatClient = client;
    }

    private Task<ChatCompletion> CompleteAsync(
        IList<ChatMessage> chatMessages,
        ChatOptions? options = null,
        CancellationToken cancellationToken = default)
    {
        return ChatClient.CompleteAsync(chatMessages, options, cancellationToken);
    }

    private IAsyncEnumerable<StreamingChatCompletionUpdate> CompleteStreamingAsync(
        IList<ChatMessage> chatMessages,
        ChatOptions? options = null,
        CancellationToken cancellationToken = default)
    {
        return ChatClient.CompleteStreamingAsync(chatMessages, options, cancellationToken);
    }

}
