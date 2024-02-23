using Microsoft.AI.DevTeam.Skills;
using Microsoft.Extensions.Logging;
using Microsoft.SemanticKernel;
using Microsoft.SemanticKernel.Connectors.AI.OpenAI;
using Microsoft.SemanticKernel.Memory;
using Microsoft.SemanticKernel.Orchestration;
using Orleans.Runtime;
using Orleans.Streams;

namespace Microsoft.AI.DevTeam;

//[RegexImplicitStreamSubscription("")]
[ImplicitStreamSubscription("developers")]
public class Dev : AiAgent
{
    private readonly IKernel _kernel;
    private readonly ISemanticTextMemory _memory;
    private readonly ILogger<Dev> _logger;

    public Dev([PersistentState("state", "messages")] IPersistentState<AgentState> state, IKernel kernel, ISemanticTextMemory memory, ILogger<Dev> logger) : base(state)
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
            case EventType.CodeGenerationRequested:
                var code = await GenerateCode(item.Message);
                //await _ghService.PostComment(item.Data["org"], item.Data["repo"], long.Parse(item.Data["issueNumber"]), code);
                // postEvent EventType.CodeGenerated
                break;
            case EventType.ChainClosed:
                await CloseImplementation();
                // postEvent EventType.CodeFinished
                break;
            default:
                break;
        }
    }

    public async Task<string> GenerateCode(string ask)
    {
        try
        {
            return await CallFunction(Developer.Implement, ask, _kernel, _memory);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error generating code");
            return default;
        }
    }

    public Task<string> ReviewPlan(string plan)
    {
        throw new NotImplementedException();
    }

    public async Task CloseImplementation()
    {
        // var dev = _grains.GetGrain<IDevelopCode>(issueNumber, suffix);
        // var code = await dev.GetLastMessage();
        // var lookup = _grains.GetGrain<ILookupMetadata>(suffix);
        // var parentIssue = await lookup.GetMetadata((int)issueNumber);
        // await _azService.Store(new SaveOutputRequest
        // {
        //     ParentIssueNumber = parentIssue.IssueNumber,
        //     IssueNumber = (int)issueNumber,
        //     Output = code,
        //     Extension = "sh",
        //     Directory = "output",
        //     FileName = "run",
        //     Org = org,
        //     Repo = repo
        // });
        // var sandboxRequest = new SandboxRequest
        // {
        //     Org = org,
        //     Repo = repo,
        //     IssueNumber = (int)issueNumber,
        //     ParentIssueNumber = parentIssue.IssueNumber
        // };
        // await _azService.RunInSandbox(sandboxRequest);

        // var commitRequest = new CommitRequest
        // {
        //     Dir = "output",
        //     Org = org,
        //     Repo = repo,
        //     ParentNumber = parentIssue.IssueNumber,
        //     Number = (int)issueNumber,
        //     Branch = $"sk-{parentIssue.IssueNumber}"
        // };
        // var markTaskCompleteRequest = new MarkTaskCompleteRequest
        // {
        //     Org = org,
        //     Repo = repo,
        //     CommentId = parentIssue.CommentId
        // };

        // var sandbox = _grains.GetGrain<IManageSandbox>(issueNumber, suffix);
        // await sandbox.ScheduleCommitSandboxRun(commitRequest, markTaskCompleteRequest, sandboxRequest);
    }

    public async Task<UnderstandingResult> BuildUnderstanding(string content)
    {
        try
        {
            var explainFunction = _kernel.CreateSemanticFunction(Developer.Explain, new OpenAIRequestSettings { MaxTokens = 15000, Temperature = 0.8, TopP = 1 });
            var consolidateFunction = _kernel.CreateSemanticFunction(Developer.ConsolidateUnderstanding, new OpenAIRequestSettings { MaxTokens = 15000, Temperature = 0.8, TopP = 1 });
            var explainContext = new ContextVariables();
            explainContext.Set("input", content);
            var explainResult = await _kernel.RunAsync(explainContext, explainFunction);
            var explainMesage = explainResult.ToString();

            var consolidateContext = new ContextVariables();
            consolidateContext.Set("input", _state.State.Understanding);
            consolidateContext.Set("newUnderstanding", explainMesage);

            var consolidateResult = await _kernel.RunAsync(consolidateContext, consolidateFunction);
            var consolidateMessage = consolidateResult.ToString();

            _state.State.Understanding = consolidateMessage;
            await _state.WriteStateAsync();

            return new UnderstandingResult
            {
                NewUnderstanding = consolidateMessage,
                Explanation = explainMesage
            };
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error building understanding");
            return default;
        }
    }
}

[GenerateSerializer]
public class UnderstandingResult
{
    [Id(0)]
    public string NewUnderstanding { get; set; }
    [Id(1)]
    public string Explanation { get; set; }
}