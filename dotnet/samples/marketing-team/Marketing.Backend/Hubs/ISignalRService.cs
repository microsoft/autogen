// Copyright (c) Microsoft Corporation. All rights reserved.
// ISignalRService.cs

namespace Marketing.Backend.Hubs;

public interface ISignalRService
{
    Task SendMessageToSpecificClient(string userId, string message, AgentTypes agentType);
}
