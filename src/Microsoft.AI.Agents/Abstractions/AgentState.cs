namespace Microsoft.AI.Agents.Abstractions;

public class AgentState<T>
{
    public List<ChatHistoryItem> History { get; set; }
    public T Data { get; set; }
}
