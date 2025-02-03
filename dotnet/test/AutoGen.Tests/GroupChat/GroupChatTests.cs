// Copyright (c) Microsoft Corporation. All rights reserved.
// GroupChatTests.cs

using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using FluentAssertions;
using Moq;
using Xunit;

namespace AutoGen.Tests;

[Trait("Category", "UnitV1")]
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

        chatHistory.Count.Should().Be(10);
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

        chatHistory.Count.Should().Be(3);
        chatHistory.Last().From.Should().Be("Cathy");
    }

    [Fact]
    public async Task ItSendAsyncDoesntAddDuplicateInitializeMessagesTest()
    {
        // fix #3268
        var alice = new DefaultReplyAgent("Alice", "I am alice");
        var bob = new DefaultReplyAgent("Bob", "I am bob");
        var cathy = new DefaultReplyAgent("Cathy", $"I am cathy, {GroupChatExtension.TERMINATE}");

        var roundRobinOrchestrator = new RoundRobinOrchestrator();
        var orchestrator = Mock.Of<IOrchestrator>();
        Mock.Get(orchestrator).Setup(x => x.GetNextSpeakerAsync(It.IsAny<OrchestrationContext>(), It.IsAny<CancellationToken>()))
            .Returns((OrchestrationContext context, CancellationToken token) =>
            {
                // determine if initialize message is already sent and not added twice
                context.ChatHistory.Where(x => x.From == alice.Name).Count().Should().Be(1);

                return roundRobinOrchestrator.GetNextSpeakerAsync(context, token);
            });

        var groupChat = new GroupChat([alice, bob, cathy], orchestrator);
        groupChat.AddInitializeMessage(new TextMessage(Role.User, "Hello", from: alice.Name));

        var maxRound = 2;
        var chatHistory = new List<IMessage>();
        await foreach (var message in groupChat.SendAsync(chatHistory, maxRound))
        {
            chatHistory.Add(message);
        }

        chatHistory.Count.Should().Be(2);
    }

    [Fact]
    public async Task ItTerminateConversationWhenNoSpeakerAvailable()
    {
        // fix #3306
        var alice = new DefaultReplyAgent("Alice", "I am alice");
        var bob = new DefaultReplyAgent("Bob", "I am bob");
        var cathy = new DefaultReplyAgent("Cathy", $"I am cathy, {GroupChatExtension.TERMINATE}");

        var orchestrator = Mock.Of<IOrchestrator>();
        Mock.Get(orchestrator).Setup(x => x.GetNextSpeakerAsync(It.IsAny<OrchestrationContext>(), It.IsAny<CancellationToken>()))
            .ReturnsAsync((IAgent?)null);

        var groupChat = new GroupChat([alice, bob, cathy], orchestrator);

        var chatHistory = new List<IMessage>();

        var maxRound = 10;
        await foreach (var message in groupChat.SendAsync(chatHistory, maxRound))
        {
            chatHistory.Add(message);
        }

        chatHistory.Count.Should().Be(0);
    }
}
