// Copyright (c) Microsoft Corporation. All rights reserved.
// AiAgent.cs

using Microsoft.AutoGen.Core;
using Microsoft.Extensions.AI;

namespace DevTeam.Agents;

public class AiAgent<T>(AgentsMetadata eventTypes, IChatClient chat, ILogger<AiAgent<T>> logger) : Agent(eventTypes, logger)
{
    protected async Task AddKnowledge(string instruction, string v)
    {
        throw new NotImplementedException();
    }

    protected async Task<string> CallFunction(string prompt, ChatOptions? chatOptions=null)
    {
        if (chatOptions == null)
        {
            chatOptions = new ChatOptions() {
                Temperature = 0.8f,
                TopP = 1,
                MaxOutputTokens = 4096
            };
        }
        var response = await chat.CompleteAsync(prompt, chatOptions);
        return response.Message.Text!;
    }
}
