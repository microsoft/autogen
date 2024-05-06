using Marketing.Events;
using Marketing.Options;
using Microsoft.AI.Agents.Abstractions;
using Microsoft.AI.Agents.Orleans;
using Microsoft.SemanticKernel;
using Microsoft.SemanticKernel.Memory;
using Orleans.Runtime;

namespace Marketing.Agents;

[ImplicitStreamSubscription(Consts.OrleansNamespace)]
public class CommunityManager : AiAgent<CommunityManagerState>
{
    protected override string Namespace => Consts.OrleansNamespace;

    private readonly ILogger<GraphicDesigner> _logger;

    public CommunityManager([PersistentState("state", "messages")] IPersistentState<AgentState<CommunityManagerState>> state, Kernel kernel, ISemanticTextMemory memory, ILogger<GraphicDesigner> logger) 
    : base(state, memory, kernel)
    {
        _logger = logger;
    }

    public async override Task HandleEvent(Event item)
    {
        switch (item.Type)
        {
            case nameof(EventTypes.UserConnected):
                // The user reconnected, let's send the last message if we have one
                string lastMessage = _state.State.History.LastOrDefault()?.Message;
                if (lastMessage == null)
                {
                    return;
                }

                await SendDesignedCreatedEvent(lastMessage, item.Data["UserId"]);
                break;

            case nameof(EventTypes.ArticleCreated):                
                //var lastCode = _state.State.History.Last().Message;

                _logger.LogInformation($"[{nameof(GraphicDesigner)}] Event {nameof(EventTypes.ArticleCreated)}. UserMessage: {item.Message}");
                    
                var context = new KernelArguments { ["input"] = AppendChatHistory(item.Message) };
                string socialMediaPost = await CallFunction(CommunityManagerPrompts.WritePost, context);
                _state.State.Data.WrittenSocialMediaPost = socialMediaPost;
                await SendDesignedCreatedEvent(socialMediaPost, item.Data["UserId"]);
                break;

            default:
                break;
        }
    }

    private async Task SendDesignedCreatedEvent(string socialMediaPost, string userId)
    {
        await PublishEvent(Consts.OrleansNamespace, this.GetPrimaryKeyString(), new Event
        {
            Type = nameof(EventTypes.SocialMediaPostCreated),
            Data = new Dictionary<string, string> {
                            { "UserId", userId },
                        },
            Message = socialMediaPost
        });
    }

    public Task<String> GetArticle()
    {
        return Task.FromResult(_state.State.Data.WrittenSocialMediaPost);
    }
}