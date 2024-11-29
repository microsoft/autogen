// Copyright (c) Microsoft Corporation. All rights reserved.
// ProductManager.cs

using DevTeam.Shared;
using Microsoft.AutoGen.Core;

namespace DevTeam.Agents;

[TopicSubscription("devteam")]
public class ProductManager(RuntimeContext context, [FromKeyedServices("EventTypes")] EventTypes typeRegistry, ILogger<ProductManager> logger)
    : AiAgent<ProductManagerState>(context, typeRegistry, logger), IManageProducts,
    IHandle<ReadmeChainClosed>,
    IHandle<ReadmeRequested>
{
    public async Task Handle(ReadmeChainClosed item, CancellationToken cancellationToken = default)
    {
        // TODO: Get readme from state
        var lastReadme = ""; // _state.State.History.Last().Message
        var evt = new ReadmeCreated
        {
            Readme = lastReadme
        };
        await PublishMessageAsync(evt);
    }

    public async Task Handle(ReadmeRequested item, CancellationToken cancellationToken = default)
    {
        var readme = await CreateReadme(item.Ask);
        var evt = new ReadmeGenerated
        {
            Readme = readme,
            Org = item.Org,
            Repo = item.Repo,
            IssueNumber = item.IssueNumber
        };
        await PublishMessageAsync(evt);
    }

    public async Task<string> CreateReadme(string ask)
    {
        try
        {
            //var context = new KernelArguments { ["input"] = AppendChatHistory(ask) };
            //var instruction = "Consider the following architectural guidelines:!waf!";
            //var enhancedContext = await AddKnowledge(instruction, "waf", context);
            return await CallFunction(PMSkills.Readme);
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "Error creating readme");
            return "";
        }
    }
}

public interface IManageProducts
{
    public Task<string> CreateReadme(string ask);
}
