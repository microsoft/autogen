// Copyright (c) Microsoft Corporation. All rights reserved.
// WorkflowOrchestratorTests.cs

using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using FluentAssertions;
using Xunit;

namespace AutoGen.Tests;

public class WorkflowOrchestratorTests
{
    [Fact]
    public async Task ItReturnNextAgentAsync()
    {
        var workflow = new Graph();
        var alice = new EchoAgent("Alice");
        var bob = new EchoAgent("Bob");
        var charlie = new EchoAgent("Charlie");
        workflow.AddTransition(Transition.Create(alice, bob));
        workflow.AddTransition(Transition.Create(bob, charlie));
        workflow.AddTransition(Transition.Create(charlie, alice));
        var orchestrator = new WorkflowOrchestrator(workflow);
        var context = new OrchestrationContext
        {
            Candidates = [alice, bob, charlie]
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
            var result = await orchestrator.GetNextSpeakerAsync(context);
            Assert.Equal(expect, result!.Name);
        }
    }

    [Fact]
    public async Task ItReturnNullIfNoCandidates()
    {
        var workflow = new Graph();
        var orchestrator = new WorkflowOrchestrator(workflow);
        var context = new OrchestrationContext
        {
            Candidates = new List<IAgent>(),
            ChatHistory = new List<IMessage>
            {
                new TextMessage(Role.User, "Hello, Alice", from: "Alice"),
            },
        };

        var nextAgent = await orchestrator.GetNextSpeakerAsync(context);
        nextAgent.Should().BeNull();
    }

    [Fact]
    public async Task ItReturnNullIfNoAgentIsAvailableFromWorkflowAsync()
    {
        var workflow = new Graph();
        var alice = new EchoAgent("Alice");
        var bob = new EchoAgent("Bob");
        workflow.AddTransition(Transition.Create(alice, bob));
        var orchestrator = new WorkflowOrchestrator(workflow);
        var context = new OrchestrationContext
        {
            Candidates = [alice, bob],
            ChatHistory = new List<IMessage>
            {
                new TextMessage(Role.User, "Hello, Bob", from: "Bob"),
            },
        };

        var nextSpeaker = await orchestrator.GetNextSpeakerAsync(context);
        nextSpeaker.Should().BeNull();
    }

    [Fact]
    public async Task ItThrowExceptionWhenMoreThanOneAvailableAgentsFromWorkflowAsync()
    {
        var workflow = new Graph();
        var alice = new EchoAgent("Alice");
        var bob = new EchoAgent("Bob");
        var charlie = new EchoAgent("Charlie");
        workflow.AddTransition(Transition.Create(alice, bob));
        workflow.AddTransition(Transition.Create(alice, charlie));
        var orchestrator = new WorkflowOrchestrator(workflow);
        var context = new OrchestrationContext
        {
            Candidates = [alice, bob, charlie],
            ChatHistory = new List<IMessage>
            {
                new TextMessage(Role.User, "Hello, Bob", from: "Alice"),
            },
        };

        var action = async () => await orchestrator.GetNextSpeakerAsync(context);

        await action.Should().ThrowExactlyAsync<ArgumentException>().WithMessage("There are more than one available agents from the workflow for the next speaker.");
    }
}
