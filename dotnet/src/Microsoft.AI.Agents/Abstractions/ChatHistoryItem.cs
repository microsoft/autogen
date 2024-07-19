namespace Microsoft.AI.Agents.Abstractions;

[Serializable]
public class ChatHistoryItem
{
    public required string Message { get; set; }
    public ChatUserType UserType { get; set; }
    public int Order { get; set; }
}
