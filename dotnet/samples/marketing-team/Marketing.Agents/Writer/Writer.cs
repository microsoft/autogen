// Copyright (c) Microsoft Corporation. All rights reserved.
// Writer.cs

using Marketing.Shared;
using Microsoft.SemanticKernel.Memory;
using Microsoft.SemanticKernel;
using Microsoft.AutoGen.Agents;
using Microsoft.AutoGen.Abstractions;

namespace Marketing.Agents;

[TopicSubscription("default")]
public class Writer(IAgentContext context, Kernel kernel, ISemanticTextMemory memory, [FromKeyedServices("EventTypes")] EventTypes typeRegistry, ILogger<Writer> logger)
    : SKAiAgent<WriterState>(context, memory, kernel, typeRegistry),
    IHandle<UserConnected>,
    IHandle<UserChatInput>,
    IHandle<AuditorAlert>
{
    public async Task Handle(UserConnected item)
    {
        logger.LogInformation($"User Connected: {item.UserId}");
        string? lastMessage = _state.History.LastOrDefault()?.Message;
        if (string.IsNullOrWhiteSpace(lastMessage))
        {
            return;
        }

        await SendArticleCreatedEvent(lastMessage, item.UserId);
    }

    public async Task Handle(UserChatInput item)
    {
        logger.LogInformation($"UserChatInput: {item.UserMessage}");
        var context = new KernelArguments { ["input"] = AppendChatHistory(item.UserMessage) };
        var newArticle = await CallFunction(WriterPrompts.Write, context);

        if (newArticle.Contains("NOTFORME", StringComparison.InvariantCultureIgnoreCase))
        {
            return;
        }
        // TODO: Implement
       // var agentState = _state.Data.ToAgentState(this.AgentId, "Etag");
      //  await Store("WrittenArticle", newArticle);
        await SendArticleCreatedEvent(newArticle, item.UserId);
    }

    public async Task Handle(AuditorAlert item)
    {
        logger.LogInformation($"Auditor feedback: {item.AuditorAlertMessage}");
        var context = new KernelArguments { ["input"] = AppendChatHistory(item.AuditorAlertMessage) };
        var newArticle = await CallFunction(WriterPrompts.Adjust, context);

        if (newArticle.Contains("NOTFORME", StringComparison.InvariantCultureIgnoreCase))
        {
            return;
        }
        await SendArticleCreatedEvent(newArticle, item.UserId);
    }
    private async Task SendArticleCreatedEvent(string article, string userId)
    {
        var articleCreatedEvent = new ArticleCreated
        {
            Article = article,
            UserId = userId
        }.ToCloudEvent(this.AgentId.Key);

        var auditTextEvent = new AuditText
        {
            Text = "Article written by the Writer: " + article,
            UserId = userId
        }.ToCloudEvent(this.AgentId.Key);

        await PublishEvent(articleCreatedEvent);
        await PublishEvent(auditTextEvent);
    }

    //protected override Task<RpcResponse> HandleRequest(RpcRequest request) => request.Method switch
    //{
    //    "GetArticle" => Task.FromResult(new RpcResponse
    //    {
    //        Payload = new Payload
    //        {
    //            DataContentType = "text/plain",
    //            Data = ByteString.CopyFromUtf8(_state.Data.WrittenArticle),
    //            DataType = "text"
    //        }
    //    }),
    //    _ => Task.FromResult(new RpcResponse { Error = $"Unknown method, '{request.Method}'." }),
    //};

    public Task<string> GetArticle()
    {
        return Task.FromResult(_state.Data.WrittenArticle);
    }
}
