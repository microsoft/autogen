// Copyright (c) Microsoft Corporation. All rights reserved.
// RolePlayToolCallOrchestratorTests.cs

using System;
using System.Collections.Generic;
using System.Threading.Tasks;
using AutoGen.OpenAI.Orchestrator;
using AutoGen.Tests;
using Azure.AI.OpenAI;
using FluentAssertions;
using Moq;
using OpenAI;
using OpenAI.Chat;
using Xunit;

namespace AutoGen.OpenAI.Tests;

public class RolePlayToolCallOrchestratorTests
{
    [Fact]
    public async Task ItReturnNullWhenNoCandidateIsAvailableAsync()
    {
        var chatClient = Mock.Of<ChatClient>();
        var orchestrator = new RolePlayToolCallOrchestrator(chatClient);
        var context = new OrchestrationContext
        {
            Candidates = [],
            ChatHistory = [],
        };

        var speaker = await orchestrator.GetNextSpeakerAsync(context);
        speaker.Should().BeNull();
    }

    [Fact]
    public async Task ItReturnCandidateWhenOnlyOneCandidateIsAvailableAsync()
    {
        var chatClient = Mock.Of<ChatClient>();
        var alice = new EchoAgent("Alice");
        var orchestrator = new RolePlayToolCallOrchestrator(chatClient);
        var context = new OrchestrationContext
        {
            Candidates = [alice],
            ChatHistory = [],
        };

        var speaker = await orchestrator.GetNextSpeakerAsync(context);
        speaker.Should().Be(alice);
    }

    [Fact]
    public async Task ItSelectNextSpeakerFromWorkflowIfProvided()
    {
        var workflow = new Graph();
        var alice = new EchoAgent("Alice");
        var bob = new EchoAgent("Bob");
        var charlie = new EchoAgent("Charlie");
        workflow.AddTransition(Transition.Create(alice, bob));
        workflow.AddTransition(Transition.Create(bob, charlie));
        workflow.AddTransition(Transition.Create(charlie, alice));

        var client = Mock.Of<ChatClient>();
        var orchestrator = new RolePlayToolCallOrchestrator(client, workflow);
        var context = new OrchestrationContext
        {
            Candidates = [alice, bob, charlie],
            ChatHistory =
            [
                new TextMessage(Role.User, "Hello, Bob", from: "Alice"),
            ],
        };

        var speaker = await orchestrator.GetNextSpeakerAsync(context);
        speaker.Should().Be(bob);
    }

    [Fact]
    public async Task ItReturnNullIfNoAvailableAgentFromWorkflowAsync()
    {
        var workflow = new Graph();
        var alice = new EchoAgent("Alice");
        var bob = new EchoAgent("Bob");
        workflow.AddTransition(Transition.Create(alice, bob));

        var client = Mock.Of<ChatClient>();
        var orchestrator = new RolePlayToolCallOrchestrator(client, workflow);
        var context = new OrchestrationContext
        {
            Candidates = [alice, bob],
            ChatHistory =
            [
                new TextMessage(Role.User, "Hello, Alice", from: "Bob"),
            ],
        };

        var speaker = await orchestrator.GetNextSpeakerAsync(context);
        speaker.Should().BeNull();
    }

    [ApiKeyFact("AZURE_OPENAI_API_KEY", "AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_DEPLOY_NAME")]
    public async Task GPT_3_5_CoderReviewerRunnerTestAsync()
    {
        var endpoint = Environment.GetEnvironmentVariable("AZURE_OPENAI_ENDPOINT") ?? throw new Exception("Please set AZURE_OPENAI_ENDPOINT environment variable.");
        var key = Environment.GetEnvironmentVariable("AZURE_OPENAI_API_KEY") ?? throw new Exception("Please set AZURE_OPENAI_API_KEY environment variable.");
        var deployName = Environment.GetEnvironmentVariable("AZURE_OPENAI_DEPLOY_NAME") ?? throw new Exception("Please set AZURE_OPENAI_DEPLOY_NAME environment variable.");
        var openaiClient = new AzureOpenAIClient(new Uri(endpoint), new System.ClientModel.ApiKeyCredential(key));
        var chatClient = openaiClient.GetChatClient(deployName);

        await CoderReviewerRunnerTestAsync(chatClient);
    }

    [ApiKeyFact("OPENAI_API_KEY")]
    public async Task GPT_4o_CoderReviewerRunnerTestAsync()
    {
        var apiKey = Environment.GetEnvironmentVariable("OPENAI_API_KEY") ?? throw new InvalidOperationException("OPENAI_API_KEY is not set");
        var model = "gpt-4o";
        var openaiClient = new OpenAIClient(apiKey);
        var chatClient = openaiClient.GetChatClient(model);

        await CoderReviewerRunnerTestAsync(chatClient);
    }

    [ApiKeyFact("OPENAI_API_KEY")]
    public async Task GPT_4o_mini_CoderReviewerRunnerTestAsync()
    {
        var apiKey = Environment.GetEnvironmentVariable("OPENAI_API_KEY") ?? throw new InvalidOperationException("OPENAI_API_KEY is not set");
        var model = "gpt-4o-mini";
        var openaiClient = new OpenAIClient(apiKey);
        var chatClient = openaiClient.GetChatClient(model);

        await CoderReviewerRunnerTestAsync(chatClient);
    }

    /// <summary>
    /// This test is to mimic the conversation among coder, reviewer and runner.
    /// The coder will write the code, the reviewer will review the code, and the runner will run the code.
    /// </summary>
    /// <param name="client"></param>
    /// <returns></returns>
    private async Task CoderReviewerRunnerTestAsync(ChatClient client)
    {
        var coder = new EchoAgent("Coder");
        var reviewer = new EchoAgent("Reviewer");
        var runner = new EchoAgent("Runner");
        var user = new EchoAgent("User");
        var initializeMessage = new List<IMessage>
        {
            new TextMessage(Role.User, "Hello, I am user, I will provide the coding task, please write the code first, then review and run it", from: "User"),
            new TextMessage(Role.User, "Hello, I am coder, I will write the code", from: "Coder"),
            new TextMessage(Role.User, "Hello, I am reviewer, I will review the code", from: "Reviewer"),
            new TextMessage(Role.User, "Hello, I am runner, I will run the code", from: "Runner"),
            new TextMessage(Role.User, "how to print 'hello world' using C#", from: user.Name),
        };

        var chatHistory = new List<IMessage>()
        {
            new TextMessage(Role.User, """
            ```csharp
            Console.WriteLine("Hello World");
            ```
            """, from: coder.Name),
            new TextMessage(Role.User, "The code looks good", from: reviewer.Name),
            new TextMessage(Role.User, "The code runs successfully, the output is 'Hello World'", from: runner.Name),
        };

        var orchestrator = new RolePlayToolCallOrchestrator(client);
        foreach (var message in chatHistory)
        {
            var context = new OrchestrationContext
            {
                Candidates = [coder, reviewer, runner, user],
                ChatHistory = initializeMessage,
            };

            var speaker = await orchestrator.GetNextSpeakerAsync(context);
            speaker!.Name.Should().Be(message.From);
            initializeMessage.Add(message);
        }

        // the last next speaker should be the user
        var lastSpeaker = await orchestrator.GetNextSpeakerAsync(new OrchestrationContext
        {
            Candidates = [coder, reviewer, runner, user],
            ChatHistory = initializeMessage,
        });

        lastSpeaker!.Name.Should().Be(user.Name);
    }
}
