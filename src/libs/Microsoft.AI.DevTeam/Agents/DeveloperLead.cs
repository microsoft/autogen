using Microsoft.AI.DevTeam.Skills;
using Microsoft.Extensions.Logging;
using Microsoft.SemanticKernel;
using Microsoft.SemanticKernel.Memory;
using Orleans.Runtime;
using Orleans.Streams;
using System.Text.Json;

namespace Microsoft.AI.DevTeam;
[ImplicitStreamSubscription(Consts.MainNamespace)]
public class DeveloperLead : AiAgent
{
    private readonly IKernel _kernel;
    private readonly ISemanticTextMemory _memory;
    private readonly ILogger<DeveloperLead> _logger;

    private readonly IManageGithub _ghService;

    public DeveloperLead([PersistentState("state", "messages")] IPersistentState<AgentState> state, IKernel kernel, ISemanticTextMemory memory, ILogger<DeveloperLead> logger, IManageGithub ghService) : base(state)
    {
        _kernel = kernel;
        _memory = memory;
        _logger = logger;
        _ghService = ghService;
    }
    public async override Task OnActivateAsync(CancellationToken cancellationToken)
    {
        var streamProvider = this.GetStreamProvider("StreamProvider");
        var streamId = StreamId.Create(Consts.MainNamespace, this.GetPrimaryKeyString());
        var stream = streamProvider.GetStream<Event>(streamId);

        await stream.SubscribeAsync(HandleEvent);
    }

    public async override Task HandleEvent(Event item, StreamSequenceToken? token)
    {
        switch (item.Type)
        {
            case EventType.DevPlanRequested:
                var plan = await CreatePlan(item.Message);
                 await PublishEvent(Consts.MainNamespace, this.GetPrimaryKeyString(), new Event {
                     Type = EventType.DevPlanGenerated,
                        Data = new Dictionary<string, string> {
                            { "org", item.Data["org"] },
                            { "repo", item.Data["repo"] },
                            { "issueNumber", item.Data["issueNumber"] },
                            { "plan", plan }
                        },
                       Message = plan
                });
                break;
            case EventType.ChainClosed:
                await ClosePlan(item.Data["org"], item.Data["repo"], long.Parse(item.Data["issueNumber"]), long.Parse(item.Data["parentNumber"]));
                // postEvent EventType.DevPlanFinished
                break;
            default:
                break;
        }
    }
    public async Task<string> CreatePlan(string ask)
    {
        try
        {
            return await CallFunction(DevLead.Plan, ask, _kernel, _memory);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error creating development plan");
            return default;
        }
    }

    public async Task ClosePlan(string org, string repo, long issueNumber, long parentNumber)
    {
        var plan = await GetLatestPlan();
        var suffix = $"{org}-{repo}";
        var streamProvider = this.GetStreamProvider("StreamProvider");
        var streamId = StreamId.Create(Consts.MainNamespace, suffix+parentNumber.ToString());
        var stream = streamProvider.GetStream<Event>(streamId);

        var eventTasks = plan.steps.SelectMany(s => s.subtasks.Select(st => stream.OnNextAsync(new Event {
            Type = EventType.NewAsk,
            Data = new Dictionary<string, string>
            {
                { "org", org },
                { "repo", repo },
                { "parentNumber", parentNumber.ToString()}
            },
            Message = st.prompt
        })));
        
        Task.WaitAll(eventTasks.ToArray());
        //await conductor.ImplementationFlow(plan, org, repo, parentIssue.IssueNumber);

        // await _ghService.MarkTaskComplete(new MarkTaskCompleteRequest
        // {
        //     Org = org,
        //     Repo = repo,
        //     CommentId = _state.State.CommentId
        // });
    }

    public Task<DevLeadPlanResponse> GetLatestPlan()
    {
        var plan = _state.State.History.Last().Message;
        var response = JsonSerializer.Deserialize<DevLeadPlanResponse>(plan);
        return Task.FromResult(response);
    }
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




