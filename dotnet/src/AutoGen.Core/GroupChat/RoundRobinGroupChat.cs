// Copyright (c) Microsoft Corporation. All rights reserved.
// RoundRobinGroupChat.cs

using System;
using System.Collections.Generic;
using System.Linq;
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
        IEnumerable<IMessage>? conversationWithName = null,
        int maxRound = 10,
        CancellationToken ct = default)
    {
        var conversationHistory = new List<IMessage>();
        if (conversationWithName != null)
        {
            conversationHistory.AddRange(conversationWithName);
        }

        var lastSpeaker = conversationHistory.LastOrDefault()?.From switch
        {
            null => this.agents.First(),
            _ => this.agents.FirstOrDefault(x => x.Name == conversationHistory.Last().From) ?? throw new Exception("The agent is not in the group chat"),
        };
        var round = 0;
        while (round < maxRound)
        {
            var currentSpeaker = this.SelectNextSpeaker(lastSpeaker);
            var processedConversation = this.ProcessConversationForAgent(this.initializeMessages, conversationHistory);
            var result = await currentSpeaker.GenerateReplyAsync(processedConversation) ?? throw new Exception("No result is returned.");
            conversationHistory.Add(result);

            // if message is terminate message, then terminate the conversation
            if (result?.IsGroupChatTerminateMessage() ?? false)
            {
                break;
            }

            lastSpeaker = currentSpeaker;
            round++;
        }

        return conversationHistory;
    }

    public void SendIntroduction(IMessage message)
    {
        this.initializeMessages.Add(message);
    }

    private IAgent SelectNextSpeaker(IAgent currentSpeaker)
    {
        var index = this.agents.IndexOf(currentSpeaker);
        if (index == -1)
        {
            throw new ArgumentException("The agent is not in the group chat", nameof(currentSpeaker));
        }

        var nextIndex = (index + 1) % this.agents.Count;
        return this.agents[nextIndex];
    }
}
