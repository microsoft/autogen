using Google.Protobuf;

namespace Microsoft.AutoGen.Abstractions;

public class ChatState
    <T> where T : IMessage, new()
{
    public List<ChatHistoryItem> History { get; set; } = new();
    public T Data { get; set; } = new();
}
