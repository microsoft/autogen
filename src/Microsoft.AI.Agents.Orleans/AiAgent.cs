using System.Text;
using Microsoft.AI.Agents.Abstractions;
using Microsoft.SemanticKernel;
using Microsoft.SemanticKernel.Connectors.OpenAI;
using Microsoft.SemanticKernel.Memory;
using Orleans.Runtime;

namespace Microsoft.AI.Agents.Orleans;

public abstract class AiAgent<T> : Agent, IAiAgent where T : class, new()
{
    protected IPersistentState<AgentState<T>> _state;
    protected Kernel _kernel;
    private readonly ISemanticTextMemory _memory;
    

    public AiAgent([PersistentState("state", "messages")] IPersistentState<AgentState<T>> state, ISemanticTextMemory memory, Kernel kernel) 
    {
         _state = state;
        _memory = memory;
        _kernel = kernel;
    }

    public override Task OnActivateAsync(CancellationToken cancellationToken)
    {
        // Initialize the Agent state
        if (_state.State.History == null) _state.State.History = new List<ChatHistoryItem>();
        if (_state.State.Data == null) _state.State.Data = new T();

        return base.OnActivateAsync(cancellationToken);
    }

    public void AddToHistory(string message, ChatUserType userType) => _state.State.History.Add(new ChatHistoryItem
    {
        Message = message,
        Order = _state.State.History.Count + 1,
        UserType = userType
    });

    public string AppendChatHistory(string ask)
    {
        AddToHistory(ask, ChatUserType.User);
        return string.Join("\n", _state.State.History.Select(message => $"{message.UserType}: {message.Message}"));
    }

    public virtual async Task<string> CallFunction(string template, KernelArguments arguments, OpenAIPromptExecutionSettings? settings = null)
    {
        var propmptSettings = (settings == null) ? new OpenAIPromptExecutionSettings { MaxTokens = 18000, Temperature = 0.8, TopP = 1 }
                                                : settings;
        var function = _kernel.CreateFunctionFromPrompt(template, propmptSettings);
        var result = (await _kernel.InvokeAsync(function, arguments)).ToString();
        AddToHistory(result, ChatUserType.Agent);
        await _state.WriteStateAsync();
        return result;
    }

    /// <summary>
    /// Adds knowledge to the 
    /// </summary>
    /// <param name="instruction">The instruction string that uses the value of !index! as a placeholder to inject the data. Example:"Consider the following architectural guidelines: {waf}" </param>
    /// <param name="index">Knowledge index</param>
    /// <param name="arguments">The sk arguments, "input" is the argument </param>
    /// <returns></returns>
    public async Task<KernelArguments> AddKnowledge(string instruction, string index, KernelArguments arguments)
    {
        var documents = _memory.SearchAsync(index, arguments["input"].ToString(), 5);
        var kbStringBuilder = new StringBuilder();
        await foreach (var doc in documents)
        {
            kbStringBuilder.AppendLine($"{doc.Metadata.Text}");
        }
        arguments[index] = instruction.Replace($"!{index}!", $"{kbStringBuilder}");
        return arguments;
    }
}