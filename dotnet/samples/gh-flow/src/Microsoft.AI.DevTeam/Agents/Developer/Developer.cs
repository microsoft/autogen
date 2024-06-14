using Microsoft.AI.Agents.Abstractions;
using Microsoft.AI.Agents.Orleans;
using Microsoft.AI.DevTeam.Events;
using Microsoft.SemanticKernel;
using Microsoft.SemanticKernel.Memory;
using Orleans.Runtime;

namespace Microsoft.AI.DevTeam;

[ImplicitStreamSubscription(Consts.MainNamespace)]
public class Dev : AiAgent<DeveloperState>, IDevelopApps
{
    protected override string Namespace => Consts.MainNamespace;

    private readonly ILogger<Dev> _logger;

    public Dev([PersistentState("state", "messages")] IPersistentState<AgentState<DeveloperState>> state, Kernel kernel, ISemanticTextMemory memory, ILogger<Dev> logger)
    : base(state, memory, kernel)
    {
        _logger = logger;
    }

    public async override Task HandleEvent(Event item)
    {
        switch (item.Type)
        {
            case nameof(GithubFlowEventType.CodeGenerationRequested):
                {
                    var context = item.ToGithubContext();
                    var code = await GenerateCode(item.Data["input"]);
                    var data = context.ToData();
                    data["result"] = code;
                    await PublishEvent(Consts.MainNamespace, this.GetPrimaryKeyString(), new Event
                    {
                        Type = nameof(GithubFlowEventType.CodeGenerated),
                        Subject = context.Subject,
                        Data = data
                    });
                }

                break;
            case nameof(GithubFlowEventType.CodeChainClosed):
                {
                    var context = item.ToGithubContext();
                    var lastCode = _state.State.History.Last().Message;
                    var data = context.ToData();
                    data["code"] = lastCode;
                    await PublishEvent(Consts.MainNamespace, this.GetPrimaryKeyString(), new Event
                    {
                        Type = nameof(GithubFlowEventType.CodeCreated),
                        Subject = context.Subject,
                        Data = data
                    });
                }

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
            var context = new KernelArguments { ["input"] = AppendChatHistory(ask) };
            var instruction = "Consider the following architectural guidelines:!waf!";
            var enhancedContext = await AddKnowledge(instruction, "waf", context);
            return await CallFunction(DeveloperSkills.Implement, enhancedContext);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error generating code");
            return default;
        }
    }
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