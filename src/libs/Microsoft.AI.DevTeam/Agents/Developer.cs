using Microsoft.AI.DevTeam.Skills;
using Microsoft.Extensions.Logging;
using Microsoft.SemanticKernel;
using Microsoft.SemanticKernel.Connectors.AI.OpenAI;
using Microsoft.SemanticKernel.Memory;
using Microsoft.SemanticKernel.Orchestration;
using Orleans.Runtime;
using Orleans.Streams;

namespace Microsoft.AI.DevTeam;

[ImplicitStreamSubscription(Consts.MainNamespace)]
public class Dev : AiAgent, IDevelopApps
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

    public async override Task HandleEvent(Event item, StreamSequenceToken? token)
    {
        switch (item.Type)
        {
            case EventType.CodeGenerationRequested:
                var code = await GenerateCode(item.Message);
                await PublishEvent(Consts.MainNamespace, this.GetPrimaryKeyString(), new Event {
                     Type = EventType.CodeGenerated,
                        Data = new Dictionary<string, string> {
                            { "org", item.Data["org"] },
                            { "repo", item.Data["repo"] },
                            { "issueNumber", item.Data["issueNumber"] },
                            { "code", code }
                        },
                       Message = code
                });
                break;
            case EventType.CodeChainClosed:
                var lastCode = _state.State.History.Last().Message;
                await PublishEvent(Consts.MainNamespace, this.GetPrimaryKeyString(), new Event {
                     Type = EventType.CodeCreated,
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
            return await CallFunction(Developer.Implement, ask, _kernel, _memory);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error generating code");
            return default;
        }
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