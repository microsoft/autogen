// Copyright (c) Microsoft Corporation. All rights reserved.
// Developer.cs

using DevTeam.Agents;
using Microsoft.AutoGen.Core;

namespace DevTeam.Backend.Agents.Developer;

[TopicSubscription(Consts.TopicName)]
public class Dev([FromKeyedServices("AgentsMetadata")] AgentsMetadata typeRegistry, ILogger<Dev> logger)
    : AiAgent<DeveloperState>(typeRegistry, logger), IDevelopApps,
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
        // TODO: Read the Topic from the agent metadata
        await PublishMessageAsync(evt, topic: Consts.TopicName).ConfigureAwait(false);
    }

    public async Task Handle(CodeChainClosed item, CancellationToken cancellationToken = default)
    {
        //TODO: Get code from state
        var lastCode = ""; // _state.State.History.Last().Message
        var evt = new CodeCreated
        {
            Code = lastCode
        };
        await PublishMessageAsync(evt, topic: Consts.TopicName).ConfigureAwait(false);
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
