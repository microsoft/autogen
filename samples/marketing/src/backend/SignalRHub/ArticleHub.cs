namespace Marketing.SignalRHub;

using Microsoft.AI.Agents.Abstractions;
using Microsoft.AspNetCore.SignalR;
using Orleans.Runtime;
using Marketing.Options;
using Marketing.Events;

public class ArticleHub : Hub<IArticleHub>
{
    public override async Task OnConnectedAsync()
    {
        await base.OnConnectedAsync();
    }

    public override async Task OnDisconnectedAsync(Exception exception)
    {
        string removedUserId;
        SignalRConnectionsDB.ConnectionIdByUser.TryRemove(Context.ConnectionId, out _);
        await base.OnDisconnectedAsync(exception);
    }

    /// <summary>
    /// This method is called when a new message from the client arrives.
    /// </summary>
    /// <param name="frontEndMessage"></param>
    /// <param name="clusterClient"></param>
    /// <returns></returns>
    public async Task ProcessMessage(FrontEndMessage frontEndMessage, IClusterClient clusterClient)
    {
        var streamProvider = clusterClient.GetStreamProvider("StreamProvider");
        var streamId = StreamId.Create(Consts.OrleansNamespace, frontEndMessage.UserId);
        var stream = streamProvider.GetStream<Event>(streamId);

        var data = new Dictionary<string, string>
            {
                { "UserId", frontEndMessage.UserId },
                { "userMessage", frontEndMessage.Message},
            };

        await stream.OnNextAsync(new Event
        {
            Type = nameof(EventTypes.UserChatInput),
            Data = data
        });

    }

    public async Task ConnectToAgent(string UserId, IClusterClient clusterClient)
    {
        var frontEndMessage = new FrontEndMessage()
        {
            UserId = UserId,
            Message = "Connected to agents",
            Agent = AgentTypes.Chat.ToString()
        };

        SignalRConnectionsDB.ConnectionIdByUser.AddOrUpdate(UserId, Context.ConnectionId, (key, oldValue) => Context.ConnectionId);

        // Notify the agents that a new user got connected.
        var streamProvider = clusterClient.GetStreamProvider("StreamProvider");
        var streamId = StreamId.Create(Consts.OrleansNamespace, frontEndMessage.UserId);
        var stream = streamProvider.GetStream<Event>(streamId);
        var data = new Dictionary<string, string>
            {
                { "UserId", frontEndMessage.UserId },
                { "userMessage", frontEndMessage.Message},
            };
        await stream.OnNextAsync(new Event
        {
            Type = nameof(EventTypes.UserConnected),
            Data = data
        });
    }
}