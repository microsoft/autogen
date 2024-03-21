using Microsoft.KernelMemory;
using Microsoft.SemanticKernel;
using Orleans.Runtime;
using Microsoft.AI.Agents.Abstractions;
using Microsoft.SemanticKernel.Connectors.OpenAI;

namespace Microsoft.AI.DevTeam;

public abstract class AzureAiAgent<T> : AiAgent<T>
{
    private readonly IKernelMemory _memory;

    public AzureAiAgent([PersistentState("state", "messages")] IPersistentState<AgentState<T>> state, IKernelMemory memory) : base(state)
    {
        _memory = memory;
    }

    protected async Task<KernelArguments> AddWafContext(IKernelMemory memory, KernelArguments arguments)
    {
        var waf = await memory.AskAsync(arguments["input"].ToString(), index: "waf");
        if (!waf.NoResult) arguments["wafContext"] = $"Consider the following architectural guidelines: ${waf.Result}";
        return arguments;
    }

    protected override async Task<string> CallFunction(string template, KernelArguments arguments, Kernel kernel, OpenAIPromptExecutionSettings? settings = null)
    {
        var wafArguments = await AddWafContext(_memory, arguments);
        return await base.CallFunction(template, wafArguments, kernel, settings);
    }
}