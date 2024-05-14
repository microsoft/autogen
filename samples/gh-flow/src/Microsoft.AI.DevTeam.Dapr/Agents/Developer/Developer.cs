using Dapr.Actors;
using Dapr.Actors.Runtime;
using Dapr.Client;
using Microsoft.AI.Agents.Abstractions;
using Microsoft.AI.Agents.Dapr;
using Microsoft.AI.DevTeam.Dapr.Events;
using Microsoft.SemanticKernel;
using Microsoft.SemanticKernel.Memory;
namespace Microsoft.AI.DevTeam.Dapr;
public class Dev : AiAgent<DeveloperState>, IDaprAgent
{
    
    private readonly ILogger<Dev> _logger;

    public Dev(ActorHost host, DaprClient client, Kernel kernel, ISemanticTextMemory memory, ILogger<Dev> logger) 
    : base(host, client, memory, kernel)
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
                    await PublishEvent(Consts.PubSub, Consts.MainTopic, new Event
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
                    var lastCode = state.History.Last().Message;
                    var data = context.ToData();
                    data["code"] = lastCode;
                    await PublishEvent(Consts.PubSub, Consts.MainTopic, new Event
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
            var context = new KernelArguments { ["input"] = AppendChatHistory(ask)};
            var instruction = "Consider the following architectural guidelines:!waf!";
            var enhancedContext = await AddKnowledge(instruction, "waf",context);
            return await CallFunction(DeveloperSkills.Implement, enhancedContext);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error generating code");
            return default;
        }
    }
}

public class DeveloperState
{
    public string Understanding { get; set; }
}

public class UnderstandingResult
{
    public string NewUnderstanding { get; set; }
    public string Explanation { get; set; }
}