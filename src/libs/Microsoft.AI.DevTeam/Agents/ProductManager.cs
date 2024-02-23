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
public class ProductManager : AiAgent
{
    private readonly IKernel _kernel;
    private readonly ISemanticTextMemory _memory;
    private readonly ILogger<ProductManager> _logger;

    public ProductManager([PersistentState("state", "messages")] IPersistentState<AgentState> state, IKernel kernel, ISemanticTextMemory memory, ILogger<ProductManager> logger) : base(state)
    {
        _kernel = kernel;
        _memory = memory;
        _logger = logger;
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
            case EventType.ReadmeRequested:
                var readme = await CreateReadme(item.Message);
                //await _ghService.PostComment(item.Data["org"], item.Data["repo"], long.Parse(item.Data["issueNumber"]), readme);
                // postEvent ReadmeGenerated
                break;
            case EventType.ChainClosed:
                await CloseReadme();
                // postEvent ReadmeFinished
                break;
            default:
                break;
        }
    }
    public async Task<string> CreateReadme(string ask)
    {
        try
        {
            return await CallFunction(DevLead.Plan, ask, _kernel, _memory);
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
