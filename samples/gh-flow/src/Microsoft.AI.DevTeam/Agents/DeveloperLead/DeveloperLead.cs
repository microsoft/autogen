using Microsoft.AI.Agents.Abstractions;
using Microsoft.AI.Agents.Orleans;
using Microsoft.AI.DevTeam.Events;
using Microsoft.SemanticKernel;
using Microsoft.SemanticKernel.Memory;
using Newtonsoft.Json.Linq;
using Orleans.Runtime;

namespace Microsoft.AI.DevTeam;
[ImplicitStreamSubscription(Consts.MainNamespace)]
public class DeveloperLead : AiAgent<DeveloperLeadState>, ILeadDevelopers
{
    protected override string Namespace => Consts.MainNamespace;
    private readonly ILogger<DeveloperLead> _logger;

    public DeveloperLead([PersistentState("state", "messages")] IPersistentState<AgentState<DeveloperLeadState>> state, Kernel kernel, ISemanticTextMemory memory, ILogger<DeveloperLead> logger)
     : base(state, memory, kernel)
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
                    await PublishEvent(Consts.MainNamespace, this.GetPrimaryKeyString(), new Event
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
                    var latestPlan = _state.State.History.Last().Message;
                    var data = context.ToData();
                    data["plan"] = latestPlan;
                    await PublishEvent(Consts.MainNamespace, this.GetPrimaryKeyString(), new Event
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

public interface ILeadDevelopers
{
    public Task<string> CreatePlan(string ask);
}

[GenerateSerializer]
public class DevLeadPlanResponse
{
    [Id(0)]
    public List<Step> steps { get; set; }
}

[GenerateSerializer]
public class Step
{
    [Id(0)]
    public string description { get; set; }
    [Id(1)]
    public string step { get; set; }
    [Id(2)]
    public List<Subtask> subtasks { get; set; }
}

[GenerateSerializer]
public class Subtask
{
    [Id(0)]
    public string subtask { get; set; }
    [Id(1)]
    public string prompt { get; set; }
}

public class DeveloperLeadState
{
    public string Plan { get; set; }
}