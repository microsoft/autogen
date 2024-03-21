using Microsoft.AI.Agents.Abstractions;
using Microsoft.AI.DevTeam.Events;
using Microsoft.KernelMemory;
using Microsoft.SemanticKernel;
using Orleans.Runtime;
using Orleans.Streams;

namespace Microsoft.AI.DevTeam;

[ImplicitStreamSubscription(Consts.MainNamespace)]
public class Dev : AzureAiAgent<DeveloperState>, IDevelopApps
{
    protected override string Namespace => Consts.MainNamespace;
    private readonly Kernel _kernel;
    private readonly ILogger<Dev> _logger;

    public Dev([PersistentState("state", "messages")] IPersistentState<AgentState<DeveloperState>> state, Kernel kernel, IKernelMemory memory, ILogger<Dev> logger) 
    : base(state, memory)
    {
        _kernel = kernel;
        _logger = logger;
    }

    public async override Task HandleEvent(Event item, StreamSequenceToken? token)
    {
        switch (item.Type)
        {
            case nameof(GithubFlowEventType.CodeGenerationRequested):
                var code = await GenerateCode(item.Message);
                await PublishEvent(Consts.MainNamespace, this.GetPrimaryKeyString(), new Event
                {
                    Type = nameof(GithubFlowEventType.CodeGenerated),
                    Data = new Dictionary<string, string> {
                            { "org", item.Data["org"] },
                            { "repo", item.Data["repo"] },
                            { "issueNumber", item.Data["issueNumber"] },
                            { "code", code }
                        },
                    Message = code
                });
                break;
            case nameof(GithubFlowEventType.CodeChainClosed):
                var lastCode = _state.State.History.Last().Message;
                await PublishEvent(Consts.MainNamespace, this.GetPrimaryKeyString(), new Event
                {
                    Type = nameof(GithubFlowEventType.CodeCreated),
                    Data = new Dictionary<string, string> {
                            { "org", item.Data["org"] },
                            { "repo", item.Data["repo"] },
                            { "issueNumber", item.Data["issueNumber"] },
                            { "code", lastCode },
                            { "parentNumber", item.Data["parentNumber"] }
                        },
                    Message = lastCode
                });
                break;
            default:
                break;
        }
    }

    public async Task<string> GenerateCode(string ask)
    {
        try
        {
            // TODO: ask the architect for the high level architecture as well as the files structure of the project
            var context = new KernelArguments { ["input"] = AppendChatHistory(ask)};
            return await CallFunction(DeveloperSkills.Implement, context, _kernel);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error generating code");
            return default;
        }
    }

    // public async Task<UnderstandingResult> BuildUnderstanding(string content)
    // {
    //     try
    //     {
    //         var explainFunction = _kernel.CreateSemanticFunction(Developer.Explain, new OpenAIRequestSettings { MaxTokens = 15000, Temperature = 0.8, TopP = 1 });
    //         var consolidateFunction = _kernel.CreateSemanticFunction(Developer.ConsolidateUnderstanding, new OpenAIRequestSettings { MaxTokens = 15000, Temperature = 0.8, TopP = 1 });
    //         var explainContext = new ContextVariables();
    //         explainContext.Set("input", content);
    //         var explainResult = await _kernel.RunAsync(explainContext, explainFunction);
    //         var explainMesage = explainResult.ToString();

    //         var consolidateContext = new ContextVariables();
    //         consolidateContext.Set("input", _state.State.Understanding);
    //         consolidateContext.Set("newUnderstanding", explainMesage);

    //         var consolidateResult = await _kernel.RunAsync(consolidateContext, consolidateFunction);
    //         var consolidateMessage = consolidateResult.ToString();

    //         _state.State.Understanding = consolidateMessage;
    //         await _state.WriteStateAsync();

    //         return new UnderstandingResult
    //         {
    //             NewUnderstanding = consolidateMessage,
    //             Explanation = explainMesage
    //         };
    //     }
    //     catch (Exception ex)
    //     {
    //         _logger.LogError(ex, "Error building understanding");
    //         return default;
    //     }
    // }
}

[GenerateSerializer]
public class DeveloperState
{
    [Id(0)]
    public string Understanding { get; set; }
}

public interface IDevelopApps
{
    public Task<string> GenerateCode(string ask);
}

[GenerateSerializer]
public class UnderstandingResult
{
    [Id(0)]
    public string NewUnderstanding { get; set; }
    [Id(1)]
    public string Explanation { get; set; }
}