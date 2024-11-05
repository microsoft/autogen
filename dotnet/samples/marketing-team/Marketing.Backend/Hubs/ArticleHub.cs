// Copyright (c) Microsoft Corporation. All rights reserved.
// ArticleHub.cs

using Marketing.Shared;
using Microsoft.AspNetCore.SignalR;
using Microsoft.AutoGen.Agents;
using Microsoft.AutoGen.Runtime;

namespace Marketing.Backend.Hubs;

public class ArticleHub(AgentWorker client) : Hub<IArticleHub>
{
    public override async Task OnConnectedAsync()
    {
        await base.OnConnectedAsync();
    }

    public override async Task OnDisconnectedAsync(Exception? exception)
    {
        SignalRConnectionsDB.ConnectionIdByUser.TryRemove(Context.ConnectionId, out _);
        await base.OnDisconnectedAsync(exception);
    }

    /// <summary>
    /// This method is called when a new message from the client arrives.
    /// </summary>
    /// <param name="frontEndMessage"></param>
    /// <returns></returns>
    public async Task ProcessMessage(FrontEndMessage frontEndMessage)
    {
        ArgumentNullException.ThrowIfNull(frontEndMessage);
        ArgumentNullException.ThrowIfNull(client);

        var evt = new UserChatInput { UserId = frontEndMessage.UserId, UserMessage = frontEndMessage.Message };

        await client.PublishEventAsync(evt.ToCloudEvent(frontEndMessage.UserId));
    }

    public async Task ConnectToAgent(string userId)
    {
        ArgumentNullException.ThrowIfNull(userId);
        ArgumentNullException.ThrowIfNull(client);

        var frontEndMessage = new FrontEndMessage()
        {
            UserId = userId,
            Message = "Connected to agents",
            Agent = AgentTypes.Chat.ToString()
        };

        SignalRConnectionsDB.ConnectionIdByUser.AddOrUpdate(userId, Context.ConnectionId, (key, oldValue) => Context.ConnectionId);

        // Notify the agents that a new user got connected.
        var data = new Dictionary<string, string>
        {
            ["UserId"] = frontEndMessage.UserId,
            ["userMessage"] = frontEndMessage.Message,
        };
        var evt = new UserConnected { UserId = userId };
        await client.PublishEventAsync(evt.ToCloudEvent(userId));
    }
}
