namespace Marketing.SignalRHub;

public interface IArticleHub
{
    public Task ConnectToAgent(string UserId);

    public Task ChatMessage(FrontEndMessage frontEndMessage, IClusterClient clusterClient);

    public Task SendMessageToSpecificClient(string userId, string message);
}
