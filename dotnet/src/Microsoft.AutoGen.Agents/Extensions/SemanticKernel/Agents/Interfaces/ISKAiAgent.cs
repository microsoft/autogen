
using Microsoft.SemanticKernel;
using Microsoft.SemanticKernel.Connectors.OpenAI;
using Microsoft.AutoGen.Agents.Abstractions;

namespace Microsoft.AutoGen.Agents.Extensions.SemanticKernel;

public interface ISKAiAgent : IAgent
{
    void AddToHistory(string message, ChatUserType userType);
    string AppendChatHistory(string ask);
    Task<string> CallFunction(string template, KernelArguments arguments, OpenAIPromptExecutionSettings? settings = null);
    Task<KernelArguments> AddKnowledge(string instruction, string index, KernelArguments arguments);
}
