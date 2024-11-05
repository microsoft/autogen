// Copyright (c) Microsoft Corporation. All rights reserved.
// SignalRAgent.cs

using Marketing.Shared;
using Microsoft.SemanticKernel.Memory;
using Microsoft.SemanticKernel;
using Marketing.Backend.Hubs;
using Google.Protobuf.WellKnownTypes;
using Microsoft.AutoGen.Agents;
using Microsoft.AutoGen.Abstractions;

namespace Marketing.Backend.Agents;

[TopicSubscription("default")]
public class SignalRAgent(IAgentContext context, Kernel kernel, ISemanticTextMemory memory, [FromKeyedServices("EventTypes")] EventTypes typeRegistry, ISignalRService signalRClient)
    : SKAiAgent<Empty>(context, memory, kernel, typeRegistry),
    IHandle<ArticleCreated>,
    IHandle<GraphicDesignCreated>,
    IHandle<SocialMediaPostCreated>,
    IHandle<AuditorAlert>
{
    public async Task Handle(SocialMediaPostCreated item)
    {
        ArgumentNullException.ThrowIfNull(item);
        await signalRClient.SendMessageToSpecificClient(item.UserId, item.SocialMediaPost, Hubs.AgentTypes.CommunityManager);
    }

    public async Task Handle(ArticleCreated item)
    {
        ArgumentNullException.ThrowIfNull(item);
        await signalRClient.SendMessageToSpecificClient(item.UserId, item.Article, Hubs.AgentTypes.Chat);
    }

    public async Task Handle(GraphicDesignCreated item)
    {
        ArgumentNullException.ThrowIfNull(item);
        await signalRClient.SendMessageToSpecificClient(item.UserId, item.ImageUri, Hubs.AgentTypes.GraphicDesigner);
    }

    public async Task Handle(AuditorAlert item)
    {
        ArgumentNullException.ThrowIfNull(item);
        await signalRClient.SendMessageToSpecificClient(item.UserId, item.AuditorAlertMessage, Hubs.AgentTypes.Auditor);
    }
}
