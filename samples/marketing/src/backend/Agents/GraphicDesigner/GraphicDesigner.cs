using Marketing.Events;
using Marketing.Options;
using Microsoft.AI.Agents.Abstractions;
using Microsoft.AI.Agents.Orleans;
using Microsoft.SemanticKernel;
using Microsoft.SemanticKernel.Memory;
using Microsoft.SemanticKernel.TextToImage;
using Orleans.Runtime;

namespace Marketing.Agents;

[ImplicitStreamSubscription(Consts.OrleansNamespace)]
public class GraphicDesigner : AiAgent<GraphicDesignerState>
{
    protected override string Namespace => Consts.OrleansNamespace;

    private readonly ILogger<GraphicDesigner> _logger;
    private readonly IConfiguration _configuration;

    public GraphicDesigner([PersistentState("state", "messages")] IPersistentState<AgentState<GraphicDesignerState>> state, Kernel kernel, ISemanticTextMemory memory, ILogger<GraphicDesigner> logger, IConfiguration configuration)
    : base(state, memory, kernel)
    {
        _logger = logger;
        _configuration = configuration;
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

                SendDesignedCreatedEvent(lastMessage, item.Data["UserId"]);

                break;
            case nameof(EventTypes.ArticleCreated):
                _logger.LogInformation($"[{nameof(GraphicDesigner)}] Event {nameof(EventTypes.ArticleCreated)}. UserMessage: {item.Message}");

                var dallEService = _kernel.GetRequiredService<ITextToImageService>();
                var imageUri = await dallEService.GenerateImageAsync(item.Message, 1024, 1024);

                _state.State.Data.imageUrl = imageUri;

                SendDesignedCreatedEvent(imageUri, item.Data["UserId"]);

                break;

            default:
                break;
        }
    }

    private async Task SendDesignedCreatedEvent(string AbsoluteImageUri, string userId)
    {
        await PublishEvent(Consts.OrleansNamespace, this.GetPrimaryKeyString(), new Event
        {
            Type = nameof(EventTypes.GraphicDesignCreated),
            Data = new Dictionary<string, string> {
                            { "UserId", userId },
                        },
            Message = AbsoluteImageUri
        });
    }
}