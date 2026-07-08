// Copyright (c) Microsoft Corporation. All rights reserved.
// ProductManager.cs

using DevTeam.Agents;
using Microsoft.AutoGen.Contracts;
using Microsoft.AutoGen.Core;

namespace DevTeam.Backend.Agents.ProductManager;

[TopicSubscription(Consts.TopicName)]
public class ProductManager([FromKeyedServices("AgentsMetadata")] AgentsMetadata typeRegistry, ILogger<ProductManager> logger)
    : AiAgent<ProductManagerState>(typeRegistry, logger), IManageProducts,
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
        await PublishMessageAsync(evt, topic: Consts.TopicName).ConfigureAwait(false);
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
        await PublishMessageAsync(evt, topic: Consts.TopicName).ConfigureAwait(false);
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
