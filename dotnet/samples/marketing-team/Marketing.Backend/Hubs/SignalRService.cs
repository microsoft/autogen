// Copyright (c) Microsoft Corporation. All rights reserved.
// SignalRService.cs

using Microsoft.AspNetCore.SignalR;

namespace Marketing.Backend.Hubs;

public class SignalRService(IHubContext<ArticleHub> hubContext) : ISignalRService
{
    public async Task SendMessageToSpecificClient(string userId, string message, AgentTypes agentType)
    {
        var connectionId = SignalRConnectionsDB.ConnectionIdByUser[userId];
        var frontEndMessage = new FrontEndMessage()
        {
            UserId = userId,
            Message = message,
            Agent = agentType.ToString()
        };
        await hubContext.Clients.Client(connectionId).SendAsync("ReceiveMessage", frontEndMessage);
    }
}
