using Microsoft.SemanticKernel;
using Microsoft.SemanticKernel.Connectors.OpenAI;
using Orleans.Runtime;

namespace Microsoft.AI.Agents.Abstractions;

public abstract class AiAgent<T> : Agent
{
    public AiAgent(
        [PersistentState("state", "messages")] IPersistentState<AgentState<T>> state)
    {
        _state = state;
    }
    protected IPersistentState<AgentState<T>> _state;

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

    protected string AppendChatHistory(string ask)
    {
        AddToHistory(ask, ChatUserType.User);
        return string.Join("\n", _state.State.History.Select(message => $"{message.UserType}: {message.Message}"));
    }

    protected virtual async Task<string> CallFunction(string template, KernelArguments arguments, Kernel kernel, OpenAIPromptExecutionSettings? settings = null)
    {
        var propmptSettings = (settings == null) ? new OpenAIPromptExecutionSettings { MaxTokens = 18000, Temperature = 0.8, TopP = 1 }
                                                : settings;
        var function = kernel.CreateFunctionFromPrompt(template, propmptSettings);
        var result = (await kernel.InvokeAsync(function, arguments)).ToString();
        AddToHistory(result, ChatUserType.Agent);
        return result;
    }

    protected async Task<T> ShareContext()
    {
        return _state.State.Data;
    }
}

[Serializable]
public class ChatHistoryItem
{
    public string Message { get; set; }
    public ChatUserType UserType { get; set; }
    public int Order { get; set; }

}

public class AgentState<T>
{
    public List<ChatHistoryItem> History { get; set; }
    public T Data { get; set; }
}

public enum ChatUserType
{
    System,
    User,
    Agent
}