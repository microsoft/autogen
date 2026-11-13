// Copyright (c) Microsoft Corporation. All rights reserved.
// HelloAIAgent.cs

using Microsoft.AutoGen.Agents;
using Microsoft.AutoGen.Contracts;
using Microsoft.AutoGen.Core;
using Microsoft.Extensions.AI;

namespace Hello;

[TypeSubscription("HelloAITopic")]
public sealed class HelloAIAgent(
    IHostApplicationLifetime hostApplicationLifetime,
    AgentId id,
    IAgentRuntime runtime,
    IChatClient client,
    ILogger<InferenceAgent<NewMessageReceived>>? logger = null)
    : InferenceAgent<NewMessageReceived>(id, runtime, "Hello AI Agent", logger, client),
        IHandle<NewMessageReceived>
{
    public async ValueTask HandleAsync(NewMessageReceived item, MessageContext messageContext)
    {
        var prompt = $"Write a short limerick greeting someone named {item.Message}.";
        var response = await ChatClient.GetResponseAsync(
            prompt,
            cancellationToken: messageContext.CancellationToken);

        Console.WriteLine(response.Text);
        hostApplicationLifetime.StopApplication();
    }
}
