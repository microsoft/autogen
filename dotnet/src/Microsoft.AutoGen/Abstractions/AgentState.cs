namespace Microsoft.AutoGen.Abstractions;

public class AgentState<T> where T : class, new()
{
    public List<ChatHistoryItem> History { get; set; } = new();
    public T Data { get; set; } = new();
}
