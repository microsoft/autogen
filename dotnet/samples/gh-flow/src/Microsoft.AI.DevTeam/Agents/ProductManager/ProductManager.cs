using Microsoft.AI.Agents.Abstractions;
using Microsoft.AI.Agents.Orleans;
using Microsoft.AI.DevTeam.Events;
using Microsoft.SemanticKernel;
using Microsoft.SemanticKernel.Memory;

namespace Microsoft.AI.DevTeam;

[ImplicitStreamSubscription(Consts.MainNamespace)]
public class ProductManager : AiAgent<ProductManagerState>, IManageProducts
{
    protected override string Namespace => Consts.MainNamespace;
    private readonly ILogger<ProductManager> _logger;

    public ProductManager([PersistentState("state", "messages")] IPersistentState<AgentState<ProductManagerState>> state, Kernel kernel, ISemanticTextMemory memory, ILogger<ProductManager> logger)
    : base(state, memory, kernel)
    {
        _logger = logger;
    }

    public override async Task HandleEvent(Event item)
    {
        ArgumentNullException.ThrowIfNull(item);
        switch (item.Type)
        {
            case nameof(GithubFlowEventType.ReadmeRequested):
                {
                    var context = item.ToGithubContext();
                    var readme = await CreateReadme(item.Data["input"]);
                    var data = context.ToData();
                    data["result"] = readme;
                    await PublishEvent(new Event
                    {
                        Namespace = this.GetPrimaryKeyString(),
                        Type = nameof(GithubFlowEventType.ReadmeGenerated),
                        Subject = context.Subject,
                        Data = data
                    });
                }

                break;
            case nameof(GithubFlowEventType.ReadmeChainClosed):
                {
                    var context = item.ToGithubContext();
                    var lastReadme = _state.State.History.Last().Message;
                    var data = context.ToData();
                    data["readme"] = lastReadme;
                    await PublishEvent(new Event
                    {
                        Namespace = this.GetPrimaryKeyString(),
                        Type = nameof(GithubFlowEventType.ReadmeCreated),
                        Subject = context.Subject,
                        Data = data
                    });
                }

                break;
            default:
                break;
        }
    }

    public async Task<string> CreateReadme(string ask)
    {
        try
        {
            var context = new KernelArguments { ["input"] = AppendChatHistory(ask) };
            var instruction = "Consider the following architectural guidelines:!waf!";
            var enhancedContext = await AddKnowledge(instruction, "waf", context);
            return await CallFunction(PMSkills.Readme, enhancedContext);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error creating readme");
            return "";
        }
    }
}

public interface IManageProducts
{
    public Task<string> CreateReadme(string ask);
}

[GenerateSerializer]
public class ProductManagerState
{
    [Id(0)]
    public string? Capabilities { get; set; }
}
