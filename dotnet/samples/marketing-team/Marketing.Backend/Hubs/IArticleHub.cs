// Copyright (c) Microsoft. All rights reserved.

namespace Marketing.Backend.Hubs;

public interface IArticleHub
{
    public Task ConnectToAgent(string UserId);

    public Task ChatMessage(FrontEndMessage frontEndMessage);

    public Task SendMessageToSpecificClient(string userId, string message);
}
