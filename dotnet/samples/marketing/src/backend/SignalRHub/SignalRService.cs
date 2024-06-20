using Microsoft.AspNetCore.SignalR;

namespace Marketing.SignalRHub;

public class SignalRService : ISignalRService
{
    private readonly IHubContext<ArticleHub> _hubContext;
    public SignalRService(IHubContext<ArticleHub> hubContext)
    {
        _hubContext = hubContext;
    }

    public async Task SendMessageToSpecificClient(string userId, string message, AgentTypes agentType)
    {
        var connectionId = SignalRConnectionsDB.ConnectionIdByUser[userId];
        var frontEndMessage = new FrontEndMessage()
        {
            UserId = userId,
            Message = message,
            Agent = agentType.ToString()
        };
        await _hubContext.Clients.Client(connectionId).SendAsync("ReceiveMessage", frontEndMessage);
    }
}
