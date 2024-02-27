using Microsoft.SemanticKernel;
using Microsoft.SemanticKernel.Connectors.AI.OpenAI;
using Microsoft.SemanticKernel.Memory;
using Microsoft.SemanticKernel.Orchestration;
using Orleans.Runtime;

namespace Microsoft.AI.DevTeam;

public abstract class AiAgent : Agent
{
     public AiAgent(
         [PersistentState("state", "messages")] IPersistentState<AgentState> state)
    {
        _state = state;
    }
    protected readonly IPersistentState<AgentState> _state;
    protected async Task<ContextVariables> CreateWafContext(ISemanticTextMemory memory, string ask)
    {
        var context = new ContextVariables();
        var interestingMemories = memory.SearchAsync("waf-pages", ask, 2);
        var wafContext = "Consider the following architectural guidelines:";
        await foreach (var m in interestingMemories)
        {
            wafContext += $"\n {m.Metadata.Text}";
        }
        context.Set("input", ask);
        context.Set("wafContext", wafContext);
        return context;
    }

    protected void AddToHistory(string message, ChatUserType userType)
    {
        if (_state.State.History == null) _state.State.History = new List<ChatHistoryItem>();
        _state.State.History.Add(new ChatHistoryItem
        {
            Message = message,
            Order = _state.State.History.Count + 1,
            UserType = userType
        });
    }

    protected async Task<string> CallFunction(string template, string ask, IKernel kernel, ISemanticTextMemory memory)
    {
            var function = kernel.CreateSemanticFunction(template, new OpenAIRequestSettings { MaxTokens = 15000, Temperature = 0.8, TopP = 1 });
            var context = await CreateWafContext(memory, ask);
            var result = (await kernel.RunAsync(context, function)).ToString();
            AddToHistory(ask, ChatUserType.User);
            AddToHistory(result, ChatUserType.Agent);
            await _state.WriteStateAsync();
            return result;
    }
}


[Serializable]
public class ChatHistoryItem
{
    public string Message { get; set; }
    public ChatUserType UserType { get; set; }
    public int Order { get; set; }

}

public class AgentState
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
