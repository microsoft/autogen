using Microsoft.SemanticKernel;
using Microsoft.SemanticKernel.Connectors.OpenAI;
using Orleans.Runtime;
using Microsoft.KernelMemory;

namespace Microsoft.AI.DevTeam;

public abstract class AiAgent : Agent
{
     public AiAgent(
         [PersistentState("state", "messages")] IPersistentState<AgentState> state, IKernelMemory memory)
    {
        _state = state;
        _memory = memory;
    }
    protected readonly IPersistentState<AgentState> _state;
    private readonly IKernelMemory _memory;

    protected async Task<KernelArguments> CreateWafContext(IKernelMemory memory, string ask)
    {
        var waf = await memory.AskAsync(ask, index:"waf");
       
        return new KernelArguments{
            ["input"] = ask,
            ["wafContext"] = $"Consider the following architectural guidelines: ${waf}"
         };
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

    protected string GetChatHistory()
    {
        return string.Join("\n",_state.State.History.Select(message=> $"{message.UserType}: {message.Message}"));
    }

    protected async Task<string> CallFunction(string template, string ask, Kernel kernel)
    {
            var function = kernel.CreateFunctionFromPrompt(template, new OpenAIPromptExecutionSettings { MaxTokens = 15000, Temperature = 0.8, TopP = 1 });
            AddToHistory(ask, ChatUserType.User);
            var history = GetChatHistory();
            var context = await CreateWafContext(_memory, history);
            var result = (await kernel.InvokeAsync(function, context)).ToString();
            
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
