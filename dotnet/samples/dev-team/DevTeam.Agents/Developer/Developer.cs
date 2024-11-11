// Copyright (c) Microsoft Corporation. All rights reserved.
// Developer.cs

using DevTeam.Shared;
using Microsoft.AutoGen.Abstractions;
using Microsoft.AutoGen.Agents;
using Microsoft.SemanticKernel;
using Microsoft.SemanticKernel.Memory;

namespace DevTeam.Agents;

[TopicSubscription("devteam")]
public class Dev(IAgentContext context, Kernel kernel, ISemanticTextMemory memory, [FromKeyedServices("EventTypes")] EventTypes typeRegistry, ILogger<Dev> logger)
    : SKAiAgent<DeveloperState>(context, memory, kernel, typeRegistry), IDevelopApps,
    IHandle<CodeGenerationRequested>,
    IHandle<CodeChainClosed>
{
    public async Task Handle(CodeGenerationRequested item)
    {
        var code = await GenerateCode(item.Ask);
        var evt = new CodeGenerated
        {
            Org = item.Org,
            Repo = item.Repo,
            IssueNumber = item.IssueNumber,
            Code = code
        };
        await PublishMessageAsync(evt);
    }

    public async Task Handle(CodeChainClosed item)
    {
        //TODO: Get code from state
        var lastCode = ""; // _state.State.History.Last().Message
        var evt = new CodeCreated
        {
            Code = lastCode
        };
        await PublishMessageAsync(evt);
    }

    public async Task<string> GenerateCode(string ask)
    {
        try
        {
            var context = new KernelArguments { ["input"] = AppendChatHistory(ask) };
            var instruction = "Consider the following architectural guidelines:!waf!";
            var enhancedContext = await AddKnowledge(instruction, "waf", context);
            return await CallFunction(DeveloperSkills.Implement, enhancedContext);
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "Error generating code");
            return "";
        }
    }
}

public interface IDevelopApps
{
    public Task<string> GenerateCode(string ask);
}
