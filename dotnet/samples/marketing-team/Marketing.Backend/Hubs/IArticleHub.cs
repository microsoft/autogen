// Copyright (c) Microsoft Corporation. All rights reserved.
// IArticleHub.cs

namespace Marketing.Backend.Hubs;

public interface IArticleHub
{
    public Task ConnectToAgent(string UserId);

    public Task ChatMessage(FrontEndMessage frontEndMessage);

    public Task SendMessageToSpecificClient(string userId, string message);
}
