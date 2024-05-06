using Marketing.Events;
using Marketing.Options;
using Marketing.SignalRHub;
using Microsoft.AI.Agents.Abstractions;
using Microsoft.AI.Agents.Orleans;
using System;
using System.Security.Policy;

namespace Marketing.Agents;

[ImplicitStreamSubscription(Consts.OrleansNamespace)]
public class SignalR : Agent
{
    protected override string Namespace => Consts.OrleansNamespace;
    
    private readonly ILogger<SignalR> _logger;
    private readonly ISignalRService _signalRClient;

    public SignalR(ILogger<SignalR> logger, ISignalRService signalRClient)
    {
        _logger = logger;
        _signalRClient = signalRClient;
    }

    public async override Task HandleEvent(Event item)
    {
        switch (item.Type)
        {
            case nameof(EventTypes.ArticleCreated):
                var writenArticle = item.Message;
                await _signalRClient.SendMessageToSpecificClient(item.Data["UserId"], writenArticle, AgentTypes.Chat);
                break;

            case nameof(EventTypes.GraphicDesignCreated):
                var imageUrl = item.Message;
                await _signalRClient.SendMessageToSpecificClient(item.Data["UserId"], imageUrl, AgentTypes.GraphicDesigner);
                break;

            case nameof(EventTypes.SocialMediaPostCreated):
                var post = item.Message;
                await _signalRClient.SendMessageToSpecificClient(item.Data["UserId"], post, AgentTypes.CommunityManager);
                break;

            default:
                break;
        }
    }
}