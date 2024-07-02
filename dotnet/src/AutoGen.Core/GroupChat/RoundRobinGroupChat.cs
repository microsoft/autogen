// Copyright (c) Microsoft Corporation. All rights reserved.
// RoundRobinGroupChat.cs

using System;
using System.Collections.Generic;
using System.Threading;
using System.Threading.Tasks;

namespace AutoGen.Core;

/// <summary>
/// Obsolete: please use <see cref="RoundRobinGroupChat"/>
/// </summary>
[Obsolete("please use RoundRobinGroupChat")]
public class SequentialGroupChat : RoundRobinGroupChat
{
    [Obsolete("please use RoundRobinGroupChat")]
    public SequentialGroupChat(IEnumerable<IAgent> agents, List<IMessage>? initializeMessages = null)
        : base(agents, initializeMessages)
    {
    }
}

/// <summary>
/// A group chat that allows agents to talk in a round-robin manner.
/// </summary>
public class RoundRobinGroupChat : IGroupChat
{
    private readonly List<IAgent> agents = new List<IAgent>();
    private readonly List<IMessage> initializeMessages = new List<IMessage>();
    private readonly RoundRobinOrchestrator orchestrator = new RoundRobinOrchestrator();

    public RoundRobinGroupChat(
        IEnumerable<IAgent> agents,
        List<IMessage>? initializeMessages = null)
    {
        this.agents.AddRange(agents);
        this.initializeMessages = initializeMessages ?? new List<IMessage>();
    }

    /// <inheritdoc />
    public void AddInitializeMessage(IMessage message)
    {
        this.SendIntroduction(message);
    }

    public async Task<IEnumerable<IMessage>> CallAsync(
        IEnumerable<IMessage>? chatHistroy = null,
        int maxRound = 10,
        CancellationToken ct = default)
    {
        var conversationHistory = new List<IMessage>();
        conversationHistory.AddRange(this.initializeMessages);
        if (chatHistroy != null)
        {
            conversationHistory.AddRange(chatHistroy);
        }
        var roundLeft = maxRound;

        while (roundLeft > 0)
        {
            var orchestratorContext = new OrchestrationContext
            {
                Candidates = this.agents,
                ChatHistory = conversationHistory,
            };
            await foreach (var nextSpeaker in this.orchestrator.GetNextSpeakerAsync(orchestratorContext, roundLeft, ct))
            {
                var result = await nextSpeaker.GenerateReplyAsync(conversationHistory, cancellationToken: ct);
                conversationHistory.Add(result);

                roundLeft--;

                if (roundLeft <= 0)
                {
                    break;
                }
            }
        }

        return conversationHistory;
    }

    public void SendIntroduction(IMessage message)
    {
        this.initializeMessages.Add(message);
    }
}
