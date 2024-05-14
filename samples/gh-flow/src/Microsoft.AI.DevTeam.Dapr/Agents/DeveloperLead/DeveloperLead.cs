using Dapr.Actors;
using Dapr.Actors.Runtime;
using Dapr.Client;
using Microsoft.AI.Agents.Abstractions;
using Microsoft.AI.Agents.Dapr;
using Microsoft.AI.DevTeam.Dapr.Events;
using Microsoft.SemanticKernel;
using Microsoft.SemanticKernel.Memory;

namespace Microsoft.AI.DevTeam.Dapr;
public class DeveloperLead : AiAgent<DeveloperLeadState>, IDaprAgent
{
    private readonly ILogger<DeveloperLead> _logger;

    public DeveloperLead(ActorHost host, DaprClient client, Kernel kernel, ISemanticTextMemory memory, ILogger<DeveloperLead> logger)
     : base(host, client, memory, kernel)
    {
        _logger = logger;
    }

    public async override Task HandleEvent(Event item)
    {
        switch (item.Type)
        {
            case nameof(GithubFlowEventType.DevPlanRequested):
                {
                     var context = item.ToGithubContext();
                    var plan = await CreatePlan(item.Data["input"]);
                    var data = context.ToData();
                    data["result"] = plan;
                    await PublishEvent(Consts.PubSub,Consts.MainTopic, new Event
                    {
                        Type = nameof(GithubFlowEventType.DevPlanGenerated),
                        Subject = context.Subject,
                        Data = data
                    });
                }
                break;
            case nameof(GithubFlowEventType.DevPlanChainClosed):
                 {
                    var context = item.ToGithubContext();
                    var latestPlan = state.History.Last().Message;
                    var data = context.ToData();
                    data["plan"] = latestPlan;
                    await PublishEvent(Consts.PubSub,Consts.MainTopic, new Event
                    {
                        Type = nameof(GithubFlowEventType.DevPlanCreated),
                        Subject = context.Subject,
                        Data = data
                    });
                }
                break;
            default:
                break;
        }
    }
    public async Task<string> CreatePlan(string ask)
    {
        try
        {
            // TODO: Ask the architect for the existing high level architecture
            // as well as the file structure
            var context = new KernelArguments { ["input"] = AppendChatHistory(ask) };
            var instruction = "Consider the following architectural guidelines:!waf!";
            var enhancedContext = await AddKnowledge(instruction, "waf", context);
            return await CallFunction(DevLeadSkills.Plan, enhancedContext);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error creating development plan");
            return default;
        }
    }
}

public class DevLeadPlanResponse
{
    public List<Step> steps { get; set; }
}

public class Step
{
    public string description { get; set; }
    public string step { get; set; }
    public List<Subtask> subtasks { get; set; }
}

public class Subtask
{
    public string subtask { get; set; }
    public string prompt { get; set; }
}

public class DeveloperLeadState
{
    public string Plan { get; set; }
}