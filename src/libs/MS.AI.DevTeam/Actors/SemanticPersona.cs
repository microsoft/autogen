using Orleans.Runtime;

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