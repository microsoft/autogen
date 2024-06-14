using Marketing.Events;
using Marketing.Options;
using Microsoft.AI.Agents.Abstractions;
using Microsoft.AI.Agents.Orleans;
using Microsoft.SemanticKernel;
using Microsoft.SemanticKernel.Memory;
using Orleans.Runtime;

namespace Marketing.Agents;

[ImplicitStreamSubscription(Consts.OrleansNamespace)]
public class Writer : AiAgent<WriterState>, IWriter
{
    protected override string Namespace => Consts.OrleansNamespace;
    
    private readonly ILogger<GraphicDesigner> _logger;

    public Writer([PersistentState("state", "messages")] IPersistentState<AgentState<WriterState>> state, Kernel kernel, ISemanticTextMemory memory, ILogger<GraphicDesigner> logger) 
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

            case nameof(EventTypes.UserChatInput):                
                {
                    var userMessage = item.Data["userMessage"]; 
                    _logger.LogInformation($"[{nameof(GraphicDesigner)}] Event {nameof(EventTypes.UserChatInput)}. UserMessage: {userMessage}");
                
                    var context = new KernelArguments { ["input"] = AppendChatHistory(userMessage) };
                    string newArticle = await CallFunction(WriterPrompts.Write, context);

                    await SendDesignedCreatedEvent(newArticle, item.Data["UserId"]);
                    break;   
                }
                
            default:
                break;
        }
    }

    private async Task SendDesignedCreatedEvent(string article, string userId)
    {
        await PublishEvent(Consts.OrleansNamespace, this.GetPrimaryKeyString(), new Event
        {
            Type = nameof(EventTypes.ArticleCreated),
            Data = new Dictionary<string, string> {
                            { "UserId", userId },
                            { nameof(article), article },
                        }
        });
    }


    public Task<String> GetArticle()
    {
        return Task.FromResult(_state.State.Data.WrittenArticle);
    }
}