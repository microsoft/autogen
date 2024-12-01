// Copyright (c) Microsoft Corporation. All rights reserved.
// Developer.cs

using DevTeam.Shared;
using Microsoft.AutoGen.Core;

namespace DevTeam.Agents;

[TopicSubscription("devteam")]
public class Dev(RuntimeContext context, [FromKeyedServices("EventTypes")] EventTypes typeRegistry, ILogger<Dev> logger)
    : AiAgent<DeveloperState>(context, typeRegistry, logger), IDevelopApps,
    IHandle<CodeGenerationRequested>,
    IHandle<CodeChainClosed>
{
    public async Task Handle(CodeGenerationRequested item, CancellationToken cancellationToken = default)
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

    public async Task Handle(CodeChainClosed item, CancellationToken cancellationToken = default)
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
            //var context = new KernelArguments { ["input"] = AppendChatHistory(ask) };
            //var instruction = "Consider the following architectural guidelines:!waf!";
            //var enhancedContext = await AddKnowledge(instruction, "waf");
            return await CallFunction(DeveloperSkills.Implement);
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
