using Marketing.Events;
using Marketing.Options;
using Marketing.SignalRHub;
using Microsoft.AI.Agents.Abstractions;
using Microsoft.AI.Agents.Orleans;

namespace Marketing.Agents;

[ImplicitStreamSubscription(Consts.OrleansNamespace)]
public class SignalRAgent : Agent
{
    protected override string Namespace => Consts.OrleansNamespace;

    private readonly ILogger<SignalRAgent> _logger;
    private readonly ISignalRService _signalRClient;

    public SignalRAgent(ILogger<SignalRAgent> logger, ISignalRService signalRClient)
    {
        _logger = logger;
        _signalRClient = signalRClient;
    }

    public override async Task HandleEvent(Event item)
    {
        ArgumentNullException.ThrowIfNull(item);

        switch (item.Type)
        {
            case nameof(EventTypes.ArticleCreated):
                var writtenArticle = item.Data["article"];
                await _signalRClient.SendMessageToSpecificClient(item.Data["UserId"], writtenArticle, AgentTypes.Chat);
                break;

            case nameof(EventTypes.GraphicDesignCreated):
                var imageUrl = item.Data["imageUri"];
                await _signalRClient.SendMessageToSpecificClient(item.Data["UserId"], imageUrl, AgentTypes.GraphicDesigner);
                break;

            case nameof(EventTypes.SocialMediaPostCreated):
                var post = item.Data["socialMediaPost"];
                await _signalRClient.SendMessageToSpecificClient(item.Data["UserId"], post, AgentTypes.CommunityManager);
                break;

            default:
                break;
        }
    }
}