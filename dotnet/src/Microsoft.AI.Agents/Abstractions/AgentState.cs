namespace Microsoft.AI.Agents.Abstractions;

public class AgentState<T> where T: class, new()
{
    public List<ChatHistoryItem> History { get; set; }
    public T Data { get; set; }
}
