// Copyright (c) Microsoft Corporation. All rights reserved.
// RoundRobinOrchestratorTests.cs

using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using Xunit;

namespace AutoGen.Tests;

public class RoundRobinOrchestratorTests
{
    [Fact]
    public async Task ItReturnNextAgentAsync()
    {
        var orchestrator = new RoundRobinOrchestrator();
        var context = new OrchestrationContext
        {
            Candidates = new List<IAgent>
            {
                new EchoAgent("Alice"),
                new EchoAgent("Bob"),
                new EchoAgent("Charlie"),
            },
        };

        var messages = new List<IMessage>
        {
            new TextMessage(Role.User, "Hello, Alice", from: "Alice"),
            new TextMessage(Role.User, "Hello, Bob", from: "Bob"),
            new TextMessage(Role.User, "Hello, Charlie", from: "Charlie"),
        };

        var expected = new List<string> { "Bob", "Charlie", "Alice" };

        var zip = messages.Zip(expected);

        foreach (var (msg, expect) in zip)
        {
            context.ChatHistory = [msg];
            var result = await orchestrator.GetNextSpeakerAsync(context, 10).ToListAsync();
            Assert.Single(result);
            Assert.Equal(expect, result.First().Name);
        }
    }

    [Fact]
    public async Task ItReturnEmptyListIfNoCandidates()
    {
        var orchestrator = new RoundRobinOrchestrator();
        var context = new OrchestrationContext
        {
            Candidates = new List<IAgent>(),
            ChatHistory = new List<IMessage>
            {
                new TextMessage(Role.User, "Hello, Alice", from: "Alice"),
            },
        };

        var result = await orchestrator.GetNextSpeakerAsync(context, 10).ToListAsync();
        Assert.Empty(result);
    }

    [Fact]
    public async Task ItReturnEmptyListIfLastMessageIsNotFromCandidates()
    {
        var orchestrator = new RoundRobinOrchestrator();
        var context = new OrchestrationContext
        {
            Candidates = new List<IAgent>
            {
                new EchoAgent("Alice"),
                new EchoAgent("Bob"),
                new EchoAgent("Charlie"),
            },
            ChatHistory = new List<IMessage>
            {
                new TextMessage(Role.User, "Hello, David", from: "David"),
            },
        };

        var result = await orchestrator.GetNextSpeakerAsync(context, 10).ToListAsync();
        Assert.Empty(result);
    }

    [Fact]
    public async Task ItReturnEmptyListIfNoChatHistory()
    {
        var orchestrator = new RoundRobinOrchestrator();
        var context = new OrchestrationContext
        {
            Candidates = new List<IAgent>
            {
                new EchoAgent("Alice"),
                new EchoAgent("Bob"),
                new EchoAgent("Charlie"),
            },
        };

        var result = await orchestrator.GetNextSpeakerAsync(context, 10).ToListAsync();
        Assert.Empty(result);
    }
}
