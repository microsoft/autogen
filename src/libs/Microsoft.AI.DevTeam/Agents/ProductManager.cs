using Microsoft.AI.DevTeam.Skills;
using Microsoft.Extensions.Logging;
using Microsoft.KernelMemory;
using Microsoft.SemanticKernel;
using Orleans.Runtime;
using Orleans.Streams;

namespace Microsoft.AI.DevTeam;

[ImplicitStreamSubscription(Consts.MainNamespace)]
public class ProductManager : AiAgent, IManageProducts
{
    private readonly Kernel _kernel;
    private readonly ILogger<ProductManager> _logger;

    public ProductManager([PersistentState("state", "messages")] IPersistentState<AgentState> state, Kernel kernel, IKernelMemory memory, ILogger<ProductManager> logger) 
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
            case EventType.ReadmeRequested:
                var readme = await CreateReadme(item.Message);
                await PublishEvent(Consts.MainNamespace, this.GetPrimaryKeyString(), new Event {
                     Type = EventType.ReadmeGenerated,
                        Data = new Dictionary<string, string> {
                            { "org", item.Data["org"] },
                            { "repo", item.Data["repo"] },
                            { "issueNumber", item.Data["issueNumber"] },
                            { "readme", readme }
                        },
                       Message = readme
                });
                break;
            case EventType.ReadmeChainClosed:
                var lastReadme = _state.State.History.Last().Message;
                await PublishEvent(Consts.MainNamespace, this.GetPrimaryKeyString(), new Event {
                     Type = EventType.ReadmeCreated,
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
            return await CallFunction(PM.Readme, ask, _kernel);
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