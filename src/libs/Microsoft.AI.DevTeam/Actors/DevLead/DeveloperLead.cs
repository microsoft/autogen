using Microsoft.AI.DevTeam.Skills;
using Microsoft.Extensions.Logging;
using Microsoft.SemanticKernel;
using Microsoft.SemanticKernel.Connectors.AI.OpenAI;
using Microsoft.SemanticKernel.Memory;
using Microsoft.SemanticKernel.Orchestration;
using Orleans.Runtime;
using Orleans.Streams;
using System.Text.Json;

namespace Microsoft.AI.DevTeam;
[ImplicitStreamSubscription("DevPersonas")]
public class DeveloperLead : SemanticPersona
{
    private readonly IKernel _kernel;
    private readonly ISemanticTextMemory _memory;
    private readonly ILogger<DeveloperLead> _logger;

    private readonly IManageGithub _ghService;

    protected override string MemorySegment => "dev-lead-memory";

    public DeveloperLead([PersistentState("state", "messages")] IPersistentState<SemanticPersonaState> state, IKernel kernel, ISemanticTextMemory memory, ILogger<DeveloperLead> logger, IManageGithub ghService) : base(state)
    {
        _kernel = kernel;
        _memory = memory;
        _logger = logger;
        _ghService = ghService;
    }
    public async override Task OnActivateAsync(CancellationToken cancellationToken)
    {
        var streamProvider = this.GetStreamProvider("StreamProvider");
        var streamId = StreamId.Create("DevPersonas", this.GetPrimaryKeyString());
        var stream = streamProvider.GetStream<Event>(streamId);

        await stream.SubscribeAsync(HandleEvent);
    }

    public async Task CreateIssue(string org, string repo, long parentNumber, string input)
    {
        var devLeadIssue = await _ghService.CreateIssue(new CreateIssueRequest
        {
            Label = $"{nameof(DevLead)}.{nameof(DevLead.Plan)}",
            Org = org,
            Repo = repo,
            Input = input,
            ParentNumber = parentNumber
        });
        
         _state.State.ParentIssueNumber = parentNumber;
         _state.State.CommentId = devLeadIssue.CommentId;
        await _state.WriteStateAsync();
    }
    public async Task<string> CreatePlan(string ask)
    {
        try
        {
            var function = _kernel.CreateSemanticFunction(DevLead.Plan, new OpenAIRequestSettings { MaxTokens = 15000, Temperature = 0.4, TopP = 1 });
            var context = new ContextVariables();
            context.Set("input", ask);
            if (_state.State.History == null) _state.State.History = new List<ChatHistoryItem>();
            _state.State.History.Add(new ChatHistoryItem
            {
                Message = ask,
                Order = _state.State.History.Count + 1,
                UserType = ChatUserType.User
            });
            await AddWafContext(_memory, ask, context);
            context.Set("input", ask);

            var result = await _kernel.RunAsync(context, function);
            var resultMessage = result.ToString();
            _state.State.History.Add(new ChatHistoryItem
            {
                Message = resultMessage,
                Order = _state.State.History.Count + 1,
                UserType = ChatUserType.Agent
            });
            await _state.WriteStateAsync();

            return resultMessage;
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
        var streamId = StreamId.Create("developers", suffix+parentNumber.ToString());
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

        await _ghService.MarkTaskComplete(new MarkTaskCompleteRequest
        {
            Org = org,
            Repo = repo,
            CommentId = _state.State.CommentId
        });
    }

    public Task<DevLeadPlanResponse> GetLatestPlan()
    {
        var plan = _state.State.History.Last().Message;
        var response = JsonSerializer.Deserialize<DevLeadPlanResponse>(plan);
        return Task.FromResult(response);
    }

    public async override Task HandleEvent(Event item, StreamSequenceToken? token)
    {
        switch (item.Type)
        {
            case EventType.NewAsk:
                await CreateIssue(item.Data["org"],  item.Data["repo"], long.Parse(item.Data["issueNumber"]) , item.Message);
                break;
            case EventType.NewAskPlan:
                var plan = await CreatePlan(item.Message);
                await _ghService.PostComment(item.Data["org"], item.Data["repo"], long.Parse(item.Data["issueNumber"]), plan);
                break;
            case EventType.ChainClosed:
                await ClosePlan(item.Data["org"], item.Data["repo"], long.Parse(item.Data["issueNumber"]), long.Parse(item.Data["parentNumber"]));
                break;
            default:
                break;
        }
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




