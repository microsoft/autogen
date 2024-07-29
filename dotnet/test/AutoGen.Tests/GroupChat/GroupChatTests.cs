// Copyright (c) Microsoft Corporation. All rights reserved.
// GroupChatTests.cs

using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using FluentAssertions;
using Xunit;

namespace AutoGen.Tests;

public class GroupChatTests
{
    [Fact]
    public async Task ItSendMessageTestAsync()
    {
        var alice = new DefaultReplyAgent("Alice", "I am alice");
        var bob = new DefaultReplyAgent("Bob", "I am bob");

        var groupChat = new GroupChat([alice, bob]);

        var chatHistory = new List<IMessage>();

        var maxRound = 10;
        await foreach (var message in groupChat.SendAsync(chatHistory, maxRound))
        {
            chatHistory.Add(message);
        }

        chatHistory.Count().Should().Be(10);
    }

    [Fact]
    public async Task ItTerminateConversationWhenAgentReturnTerminateKeyWord()
    {
        var alice = new DefaultReplyAgent("Alice", "I am alice");
        var bob = new DefaultReplyAgent("Bob", "I am bob");
        var cathy = new DefaultReplyAgent("Cathy", $"I am cathy, {GroupChatExtension.TERMINATE}");

        var groupChat = new GroupChat([alice, bob, cathy]);

        var chatHistory = new List<IMessage>();

        var maxRound = 10;
        await foreach (var message in groupChat.SendAsync(chatHistory, maxRound))
        {
            chatHistory.Add(message);
        }

        chatHistory.Count().Should().Be(3);
        chatHistory.Last().From.Should().Be("Cathy");
    }
}
