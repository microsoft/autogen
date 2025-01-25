// Copyright (c) Microsoft Corporation. All rights reserved.
// DeveloperLead.cs

using DevTeam.Agents;
using Microsoft.AutoGen.Core;

namespace DevTeam.Backend.Agents.DeveloperLead;

[TopicSubscription(Consts.TopicName)]
public class DeveloperLead([FromKeyedServices("AgentsMetadata")] AgentsMetadata typeRegistry, ILogger<DeveloperLead> logger)
    : AiAgent<DeveloperLeadState>(typeRegistry, logger), ILeadDevelopers,
    IHandle<DevPlanRequested>,
    IHandle<DevPlanChainClosed>
{
    public async Task Handle(DevPlanRequested item, CancellationToken cancellationToken = default)
    {
        var plan = await CreatePlan(item.Ask);
        var evt = new DevPlanGenerated
        {
            Org = item.Org,
            Repo = item.Repo,
            IssueNumber = item.IssueNumber,
            Plan = plan
        };
        await PublishMessageAsync(evt, topic: Consts.TopicName).ConfigureAwait(false);
    }

    public async Task Handle(DevPlanChainClosed item, CancellationToken cancellationToken = default)
    {
        // TODO: Get plan from state
        var lastPlan = ""; // _state.State.History.Last().Message
        var evt = new DevPlanCreated
        {
            Plan = lastPlan
        };
        await PublishMessageAsync(evt, topic: Consts.TopicName).ConfigureAwait(false);
    }
    public async Task<string> CreatePlan(string ask)
    {
        try
        {
            //var context = new KernelArguments { ["input"] = AppendChatHistory(ask) };
            //var instruction = "Consider the following architectural guidelines:!waf!";
            //var enhancedContext = await AddKnowledge(instruction, "waf", context);
            //var settings = new OpenAIPromptExecutionSettings
            //{
            //    ResponseFormat = "json_object",
            //    MaxTokens = 4096,
            //    Temperature = 0.8,
            //    TopP = 1
            //};
            return await CallFunction(DevLeadSkills.Plan);
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "Error creating development plan");
            return "";
        }
    }
}

public interface ILeadDevelopers
{
    public Task<string> CreatePlan(string ask);
}
