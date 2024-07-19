using Microsoft.AI.Agents.Abstractions;
using Microsoft.AI.Agents.Orleans;
using Microsoft.AI.DevTeam.Events;
using Microsoft.SemanticKernel;
using Microsoft.SemanticKernel.Connectors.OpenAI;
using Microsoft.SemanticKernel.Memory;

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

    public override async Task HandleEvent(Event item)
    {
        ArgumentNullException.ThrowIfNull(item);

        switch (item.Type)
        {
            case nameof(GithubFlowEventType.DevPlanRequested):
                {
                    var context = item.ToGithubContext();
                    var plan = await CreatePlan(item.Data["input"]);
                    var data = context.ToData();
                    data["result"] = plan;
                    await PublishEvent(new Event
                    {
                        Namespace = this.GetPrimaryKeyString(),
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
                    await PublishEvent(new Event
                    {
                        Namespace = this.GetPrimaryKeyString(),
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
            _logger.LogError(ex, "Error creating development plan");
            return "";
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
    public required List<StepDescription> Steps { get; set; }
}

[GenerateSerializer]
public class StepDescription
{
    [Id(0)]
    public string? Description { get; set; }
    [Id(1)]
    public string? Step { get; set; }
    [Id(2)]
    public List<SubtaskDescription>? Subtasks { get; set; }
}

[GenerateSerializer]
public class SubtaskDescription
{
    [Id(0)]
    public string? Subtask { get; set; }

    [Id(1)]
    public string? Prompt { get; set; }
}

public class DeveloperLeadState
{
    public string? Plan { get; set; }
}
