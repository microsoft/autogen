// Copyright (c) Microsoft. All rights reserved.

namespace Marketing.Backend.Hubs;

public interface ISignalRService
{
    Task SendMessageToSpecificClient(string userId, string message, AgentTypes agentType);
}
