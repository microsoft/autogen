using System.Text;
using Dapr.Actors;
using Dapr.Actors.Runtime;
using Dapr.Client;
using Microsoft.AI.Agents.Abstractions;
using Microsoft.SemanticKernel;
using Microsoft.SemanticKernel.Connectors.OpenAI;
using Microsoft.SemanticKernel.Memory;

namespace Microsoft.AI.Agents.Dapr;

public abstract class AiAgent<T> : Agent, IAiAgent where T: class, new()
{
    public string StateStore = "agents-statestore";
    public AiAgent(ActorHost host, DaprClient client,ISemanticTextMemory memory, Kernel kernel)
    : base(host, client)
    {
        _memory = memory;
        _kernel = kernel;
    }
    private readonly ISemanticTextMemory _memory;
    private readonly Kernel _kernel;

    protected AgentState<T> state;

   
    protected override async Task OnActivateAsync()
    {
        state = await StateManager.GetOrAddStateAsync(StateStore, new AgentState<T>());
    } 

    public void AddToHistory(string message, ChatUserType userType)
    {
        if (state.History == null) state.History = new List<ChatHistoryItem>();
        state.History.Add(new ChatHistoryItem
        {
            Message = message,
            Order = state.History.Count + 1,
            UserType = userType
        });
    }

    public string AppendChatHistory(string ask)
    {
        AddToHistory(ask, ChatUserType.User);
        return string.Join("\n", state.History.Select(message => $"{message.UserType}: {message.Message}"));
    }

    public virtual async Task<string> CallFunction(string template, KernelArguments arguments, OpenAIPromptExecutionSettings? settings = null)
    {
        var propmptSettings = (settings == null) ? new OpenAIPromptExecutionSettings { MaxTokens = 18000, Temperature = 0.8, TopP = 1 }
                                                : settings;
        var function = _kernel.CreateFunctionFromPrompt(template, propmptSettings);
        var result = (await _kernel.InvokeAsync(function, arguments)).ToString();
        AddToHistory(result, ChatUserType.Agent);
        await StateManager.SetStateAsync(
                StateStore,
                state);
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
