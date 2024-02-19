using Microsoft.AI.DevTeam.Skills;
using Microsoft.Extensions.Logging;
using Microsoft.SemanticKernel;
using Microsoft.SemanticKernel.Connectors.AI.OpenAI;
using Microsoft.SemanticKernel.Memory;
using Microsoft.SemanticKernel.Orchestration;
using Orleans.Runtime;
using Orleans.Streams;

namespace Microsoft.AI.DevTeam;

[ImplicitStreamSubscription("DevPersonas")]
public class ProductManager : SemanticPersona
{
    private readonly IKernel _kernel;
    private readonly ISemanticTextMemory _memory;
    private readonly ILogger<ProductManager> _logger;

    private readonly IManageGithub _ghService;

    protected override string MemorySegment => "pm-memory";

    public ProductManager([PersistentState("state", "messages")] IPersistentState<SemanticPersonaState> state, IKernel kernel, ISemanticTextMemory memory, ILogger<ProductManager> logger, IManageGithub ghService) : base(state)
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

    public async override Task HandleEvent(Event item, StreamSequenceToken? token)
    {
        switch (item.Type)
        {
            case EventType.NewAsk:
                await CreateIssue(item.Org, item.Repo, item.IssueNumber, item.Message);
                break;
             case EventType.NewAskReadme:
                await CreateReadme(item.Message);
                break;
            case EventType.ChainClosed:
                await CloseReadme();
                break;
            default:
                break;
        }
    }

    public async Task CreateIssue(string org, string repo, long parentNumber, string input)
    {
            // TODO: Create branch and PR
             var pmIssue = await _ghService.CreateIssue(new CreateIssueRequest
             {
                 Label = $"{nameof(PM)}.{nameof(PM.Readme)}",
                 Org = org,
                 Repo = repo,
                 Input = input,
                 ParentNumber = parentNumber
             });

             _state.State.ParentIssueNumber = parentNumber;
            await _state.WriteStateAsync();

    }
    public async Task<string> CreateReadme(string ask)
    {
        try
        {
            var function = _kernel.CreateSemanticFunction(PM.Readme, new OpenAIRequestSettings { MaxTokens = 10000, Temperature = 0.6, TopP = 1 });
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
            _logger.LogError(ex, "Error creating readme");
            return default;
        }
    }

    public async Task CloseReadme()
    {
        // var pm = _grains.GetGrain<IManageProduct>(issueNumber, suffix);
        // var readme = await pm.GetLastMessage();
        // var lookup = _grains.GetGrain<ILookupMetadata>(suffix);
        // var parentIssue = await lookup.GetMetadata((int)issueNumber);
        // await _azService.Store(new SaveOutputRequest
        // {
        //     ParentIssueNumber = parentIssue.IssueNumber,
        //     IssueNumber = (int)issueNumber,
        //     Output = readme,
        //     Extension = "md",
        //     Directory = "output",
        //     FileName = "readme",
        //     Org = org,
        //     Repo = repo
        // });
        // await _ghService.CommitToBranch(new CommitRequest
        // {
        //     Dir = "output",
        //     Org = org,
        //     Repo = repo,
        //     ParentNumber = parentIssue.IssueNumber,
        //     Number = (int)issueNumber,
        //     Branch = $"sk-{parentIssue.IssueNumber}"
        // });
        // await _ghService.MarkTaskComplete(new MarkTaskCompleteRequest
        // {
        //     Org = org,
        //     Repo = repo,
        //     CommentId = parentIssue.CommentId
        // });
    }
}
