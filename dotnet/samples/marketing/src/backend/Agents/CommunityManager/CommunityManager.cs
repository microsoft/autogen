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

    public override async Task HandleEvent(Event item)
    {
        if (item?.Type is null)
        {
            throw new ArgumentNullException(nameof(item));
        }

        switch (item.Type)
        {
            case nameof(EventTypes.UserConnected):
                // The user reconnected, let's send the last message if we have one
                var lastMessage = _state.State.History.LastOrDefault()?.Message;
                if (lastMessage == null)
                {
                    return;
                }

                await SendDesignedCreatedEvent(lastMessage, item.Data["UserId"]);
                break;

            case nameof(EventTypes.ArticleCreated):
                {
                    var article = item.Data["article"];

                    _logger.LogInformation($"[{nameof(GraphicDesigner)}] Event {nameof(EventTypes.ArticleCreated)}. Article: {{Article}}", article);

                    var context = new KernelArguments { ["input"] = AppendChatHistory(article) };
                    string socialMediaPost = await CallFunction(CommunityManagerPrompts.WritePost, context);
                    _state.State.Data.WrittenSocialMediaPost = socialMediaPost;
                    await SendDesignedCreatedEvent(socialMediaPost, item.Data["UserId"]);
                    break;
                }
            default:
                break;
        }
    }

    private async Task SendDesignedCreatedEvent(string socialMediaPost, string userId)
    {
        await PublishEvent(new Event
        {
            Namespace = this.GetPrimaryKeyString(),
            Type = nameof(EventTypes.SocialMediaPostCreated),
            Data = new Dictionary<string, string>
            {
                ["UserId"] = userId,
                [nameof(socialMediaPost)] = socialMediaPost,
            }
        });
    }

    public Task<string> GetArticle()
    {
        return Task.FromResult(_state.State.Data.WrittenSocialMediaPost);
    }
}
