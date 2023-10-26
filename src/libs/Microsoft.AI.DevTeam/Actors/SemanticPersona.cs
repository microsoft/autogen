using Microsoft.SemanticKernel;
using Microsoft.SemanticKernel.Orchestration;
using Orleans.Runtime;

namespace Microsoft.AI.DevTeam;

public abstract class SemanticPersona : Grain, IChatHistory
{
    public SemanticPersona(
         [PersistentState("state", "messages")] IPersistentState<ChatHistory> state)
    {
        _state = state;
    }
    protected virtual string MemorySegment { get; set; }
    protected List<ChatHistoryItem> History { get; set; }
    protected readonly IPersistentState<ChatHistory> _state;

    public async Task<string> GetLastMessage()
    {
        return _state.State.History.Last().Message;
    }

    protected async Task AddWafContext(IKernel kernel, string ask, ContextVariables context)
    {
        var interestingMemories = kernel.Memory.SearchAsync("waf-pages", ask, 2);
        var wafContext = "Consider the following architectural guidelines:";
        await foreach (var memory in interestingMemories)
        {
            wafContext += $"\n {memory.Metadata.Text}";
        }

        context.Set("wafContext", wafContext);
    }
}

public interface IChatHistory
{
    Task<string> GetLastMessage();
}


[Serializable]
public class ChatHistoryItem
{
    public string Message { get; set; }
    public ChatUserType UserType { get; set; }
    public int Order { get; set; }

}

public class ChatHistory
{
    public List<ChatHistoryItem> History { get; set; }
}

public enum ChatUserType
{
    System,
    User,
    Agent
}