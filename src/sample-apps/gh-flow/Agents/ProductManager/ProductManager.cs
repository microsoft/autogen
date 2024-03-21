using Microsoft.AI.Agents.Abstractions;
using Microsoft.AI.DevTeam.Events;
using Microsoft.KernelMemory;
using Microsoft.SemanticKernel;
using Orleans.Runtime;
using Orleans.Streams;

namespace Microsoft.AI.DevTeam;

[ImplicitStreamSubscription(Consts.MainNamespace)]
public class ProductManager : AzureAiAgent<ProductManagerState>, IManageProducts
{
    protected override string Namespace => Consts.MainNamespace;
    private readonly Kernel _kernel;
    private readonly ILogger<ProductManager> _logger;

    public ProductManager([PersistentState("state", "messages")] IPersistentState<AgentState<ProductManagerState>> state, Kernel kernel, IKernelMemory memory, ILogger<ProductManager> logger) 
    : base(state, memory)
    {
        _kernel = kernel;
        //_memory = memory;
        _logger = logger;
    }

    public async override Task HandleEvent(Event item, StreamSequenceToken? token)
    {
        switch (item.Type)
        {
            case nameof(GithubFlowEventType.ReadmeRequested):
                var readme = await CreateReadme(item.Message);
                await PublishEvent(Consts.MainNamespace, this.GetPrimaryKeyString(), new Event {
                     Type = nameof(GithubFlowEventType.ReadmeGenerated),
                        Data = new Dictionary<string, string> {
                            { "org", item.Data["org"] },
                            { "repo", item.Data["repo"] },
                            { "issueNumber", item.Data["issueNumber"] },
                            { "readme", readme }
                        },
                       Message = readme
                });
                break;
            case nameof(GithubFlowEventType.ReadmeChainClosed):
                var lastReadme = _state.State.History.Last().Message;
                await PublishEvent(Consts.MainNamespace, this.GetPrimaryKeyString(), new Event {
                     Type = nameof(GithubFlowEventType.ReadmeCreated),
                        Data = new Dictionary<string, string> {
                            { "org", item.Data["org"] },
                            { "repo", item.Data["repo"] },
                            { "issueNumber", item.Data["issueNumber"] },
                            { "readme", lastReadme },
                            { "parentNumber", item.Data["parentNumber"] }
                        },
                       Message = lastReadme
                });
                break;
            default:
                break;
        }
    }

    public async Task<string> CreateReadme(string ask)
    {
        try
        {
            var context = new KernelArguments { ["input"] = AppendChatHistory(ask)};
            return await CallFunction(PMSkills.Readme, context, _kernel);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error creating readme");
            return default;
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
    public string Capabilities { get; set; }
}