// Copyright (c) Microsoft Corporation. All rights reserved.
// GraphicDesigner.cs

using Marketing.Shared;
using Microsoft.AutoGen.Abstractions;
using Microsoft.AutoGen.Agents;
using Microsoft.SemanticKernel;
using Microsoft.SemanticKernel.Memory;
using Microsoft.SemanticKernel.TextToImage;

namespace Marketing.Agents;

[TopicSubscription("default")]
public class GraphicDesigner(IAgentContext context, Kernel kernel, ISemanticTextMemory memory, [FromKeyedServices("EventTypes")] EventTypes typeRegistry, ILogger<GraphicDesigner> logger)
    : SKAiAgent<GraphicDesignerState>(context, memory, kernel, typeRegistry),
    IHandle<UserConnected>,
    IHandle<ArticleCreated>
{
    public async Task Handle(UserConnected item)
    {
        var lastMessage = _state.History.LastOrDefault()?.Message;
        if (string.IsNullOrWhiteSpace(lastMessage))
        {
            return;
        }

        await SendDesignedCreatedEvent(lastMessage, item.UserId);
    }

    public async Task Handle(ArticleCreated item)
    {
        //For demo purposes, we do not recreate images if they already exist
        if (!string.IsNullOrEmpty(_state.Data.ImageUrl))
        {
            return;
        }

        logger.LogInformation($"[{nameof(GraphicDesigner)}] Event {nameof(ArticleCreated)}.");
        var dallEService = _kernel.GetRequiredService<ITextToImageService>();
        var imageUri = await dallEService.GenerateImageAsync(item.Article, 1024, 1024);

        _state.Data.ImageUrl = imageUri;

        await SendDesignedCreatedEvent(imageUri, item.UserId);
    }

    private async Task SendDesignedCreatedEvent(string imageUri, string userId)
    {
        var graphicDesignEvent = new GraphicDesignCreated
        {
            ImageUri = imageUri,
            UserId = userId
        }.ToCloudEvent(this.AgentId.Key);

        await PublishEvent(graphicDesignEvent);
    }
}
