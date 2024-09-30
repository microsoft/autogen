
using Microsoft.SemanticKernel;
using Microsoft.SemanticKernel.Connectors.OpenAI;

namespace Microsoft.AutoGen.Agents.Abstractions;

public interface IAiAgent : IAgent
{
    void AddToHistory(string message, ChatUserType userType);
    string AppendChatHistory(string ask);
    Task<string> CallFunction(string template, KernelArguments arguments, OpenAIPromptExecutionSettings? settings = null);
    Task<KernelArguments> AddKnowledge(string instruction, string index, KernelArguments arguments);
}