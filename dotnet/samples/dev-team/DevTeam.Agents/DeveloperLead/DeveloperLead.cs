using DevTeam.Shared;
using Microsoft.AutoGen.Abstractions;
using Microsoft.AutoGen.Agents;
using Microsoft.SemanticKernel;
using Microsoft.SemanticKernel.Connectors.OpenAI;
using Microsoft.SemanticKernel.Memory;

namespace DevTeam.Agents;

[TopicSubscription("devteam")]
public class DeveloperLead(IAgentContext context, Kernel kernel, ISemanticTextMemory memory, [FromKeyedServices("EventTypes")] EventTypes typeRegistry, ILogger<DeveloperLead> logger)
    : AiAgent<DeveloperLeadState>(context, memory, kernel, typeRegistry), ILeadDevelopers,
    IHandle<DevPlanRequested>,
    IHandle<DevPlanChainClosed>
{
    public async Task Handle(DevPlanRequested item)
    {
        var plan = await CreatePlan(item.Ask);
        var evt = new DevPlanGenerated
        {
            Org = item.Org,
            Repo = item.Repo,
            IssueNumber = item.IssueNumber,
            Plan = plan
        }.ToCloudEvent(this.AgentId.Key);
        await PublishEvent(evt);
    }

    public async Task Handle(DevPlanChainClosed item)
    {
        // TODO: Get plan from state
        var lastPlan = ""; // _state.State.History.Last().Message
        var evt = new DevPlanCreated
        {
            Plan = lastPlan
        }.ToCloudEvent(this.AgentId.Key);
        await PublishEvent(evt);
    }
    public async Task<string> CreatePlan(string ask)
    {
        try
        {
            var context = new KernelArguments { ["input"] = AppendChatHistory(ask) };
            var instruction = "Consider the following architectural guidelines:!waf!";
            var enhancedContext = await AddKnowledge(instruction, "waf", context);
            var settings = new OpenAIPromptExecutionSettings
            {
                ResponseFormat = "json_object",
                MaxTokens = 4096,
                Temperature = 0.8,
                TopP = 1
            };
            return await CallFunction(DevLeadSkills.Plan, enhancedContext, settings);
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
