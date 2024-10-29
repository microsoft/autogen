// Copyright (c) Microsoft. All rights reserved.

using System.Globalization;
using System.Text;
using Microsoft.SemanticKernel;
using Microsoft.SemanticKernel.Connectors.OpenAI;
using Microsoft.SemanticKernel.Memory;

namespace Microsoft.AutoGen.Agents;
public abstract class SKAiAgent<T> : AgentBase where T : class, new()
{
    protected AgentState<T> _state;
    protected Kernel _kernel;
    private readonly ISemanticTextMemory _memory;

    public SKAiAgent(IAgentContext context, ISemanticTextMemory memory, Kernel kernel, EventTypes typeRegistry) : base(context, typeRegistry)
    {
        _state = new();
        _memory = memory;
        _kernel = kernel;
    }

    public void AddToHistory(string message, ChatUserType userType) => _state.History.Add(new ChatHistoryItem
    {
        Message = message,
        Order = _state.History.Count + 1,
        UserType = userType
    });

    public string AppendChatHistory(string ask)
    {
        AddToHistory(ask, ChatUserType.User);
        return string.Join("\n", _state.History.Select(message => $"{message.UserType}: {message.Message}"));
    }

    public virtual async Task<string> CallFunction(string template, KernelArguments arguments, OpenAIPromptExecutionSettings? settings = null)
    {
        // TODO: extract this to be configurable
        var promptSettings = settings ?? new OpenAIPromptExecutionSettings { MaxTokens = 4096, Temperature = 0.8, TopP = 1 };
        var function = _kernel.CreateFunctionFromPrompt(template, promptSettings);
        var result = (await _kernel.InvokeAsync(function, arguments).ConfigureAwait(true)).ToString();
        AddToHistory(result, ChatUserType.Agent);
        //await Store(_state.Data.ToAgentState(AgentId,""));//TODO add eTag
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
        var documents = _memory.SearchAsync(index, arguments["input"]?.ToString()!, 5);
        var kbStringBuilder = new StringBuilder();
        await foreach (var doc in documents)
        {
            kbStringBuilder.AppendLine(CultureInfo.InvariantCulture, $"{doc.Metadata.Text}");
        }
        arguments[index] = instruction.Replace($"!{index}!", $"{kbStringBuilder}");
        return arguments;
    }
}

public class AgentState<T> where T : class, new()
{
    public List<ChatHistoryItem> History { get; set; } = [];
    public T Data { get; set; } = new();
}

public class ChatHistoryItem
{
    public required string Message { get; set; }
    public ChatUserType UserType { get; set; }
    public int Order { get; set; }
}

public enum ChatUserType
{
    System,
    User,
    Agent
}
