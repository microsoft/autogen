using Microsoft.SemanticKernel;
using Microsoft.SemanticKernel.Memory;
using Microsoft.SemanticKernel.Orchestration;
using Orleans.Runtime;
using Orleans.Streams;

namespace Microsoft.AI.DevTeam;

public abstract class SemanticPersona : Grain, IChatHistory
{
    public SemanticPersona(
         [PersistentState("state", "messages")] IPersistentState<SemanticPersonaState> state)
    {
        _state = state;
    }
    protected virtual string MemorySegment { get; set; }
    protected List<ChatHistoryItem> History { get; set; }
    protected readonly IPersistentState<SemanticPersonaState> _state;

    public abstract Task HandleEvent(Event item, StreamSequenceToken? token);

    public async Task<string> GetLastMessage()
    {
        return _state.State.History.Last().Message;
    }

    protected async Task AddWafContext(ISemanticTextMemory memory, string ask, ContextVariables context)
    {
        var interestingMemories = memory.SearchAsync("waf-pages", ask, 2);
        var wafContext = "Consider the following architectural guidelines:";
        await foreach (var m in interestingMemories)
        {
            wafContext += $"\n {m.Metadata.Text}";
        }

        context.Set("wafContext", wafContext);
    }

    public async override Task OnActivateAsync(CancellationToken cancellationToken)
    {
        var streamProvider = this.GetStreamProvider("");
        var streamId = StreamId.Create("MyStreamNamespace", this.GetPrimaryKey());
        var stream = streamProvider.GetStream<Event>(streamId);

        var subscriptionHandles = await stream.GetAllSubscriptionHandles();
        if ( subscriptionHandles != null && subscriptionHandles.Count > 0)
        {
            subscriptionHandles.ToList().ForEach(
                async x => await x.ResumeAsync(HandleEvent)); 
        }
        else
        {
            await stream.SubscribeAsync(HandleEvent);
        }
    }
}

public interface IChatHistory
{
    Task<string> GetLastMessage();
}

public interface IUnderstand
{
    Task<UnderstandingResult> BuildUnderstanding(string content);
}

[GenerateSerializer]
public class UnderstandingResult {
    [Id(0)]
    public string NewUnderstanding { get; set; }
    [Id(1)]
    public string Explanation { get; set; }
}

[Serializable]
public class ChatHistoryItem
{
    public string Message { get; set; }
    public ChatUserType UserType { get; set; }
    public int Order { get; set; }

}

public class SemanticPersonaState
{
    public List<ChatHistoryItem> History { get; set; }
    public string Understanding { get; set; }
}

public enum ChatUserType
{
    System,
    User,
    Agent
}