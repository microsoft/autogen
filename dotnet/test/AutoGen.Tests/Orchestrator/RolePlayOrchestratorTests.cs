// Copyright (c) Microsoft Corporation. All rights reserved.
// RolePlayOrchestratorTests.cs

using System;
using System.Collections.Generic;
using System.Linq;
using System.Net.Http;
using System.Threading;
using System.Threading.Tasks;
using AutoGen.Anthropic;
using AutoGen.Anthropic.Extensions;
using AutoGen.Anthropic.Utils;
using AutoGen.AzureAIInference;
using AutoGen.AzureAIInference.Extension;
using AutoGen.Gemini;
using AutoGen.Mistral;
using AutoGen.Mistral.Extension;
using AutoGen.OpenAI;
using AutoGen.OpenAI.Extension;
using Azure.AI.Inference;
using FluentAssertions;
using Moq;
using OpenAI;
using Xunit;

namespace AutoGen.Tests;

[Trait("Category", "UnitV1")]
public class RolePlayOrchestratorTests
{
    [Fact]
    public async Task ItReturnNextSpeakerTestAsync()
    {
        var admin = Mock.Of<IAgent>();
        Mock.Get(admin).Setup(x => x.Name).Returns("Admin");
        Mock.Get(admin).Setup(x => x.GenerateReplyAsync(
            It.IsAny<IEnumerable<IMessage>>(),
            It.IsAny<GenerateReplyOptions>(),
            It.IsAny<CancellationToken>()))
            .Callback<IEnumerable<IMessage>, GenerateReplyOptions, CancellationToken>((messages, option, _) =>
            {
                // verify prompt
                var rolePlayPrompt = messages.First().GetContent();
                rolePlayPrompt.Should().Contain("You are in a role play game. Carefully read the conversation history and carry on the conversation");
                rolePlayPrompt.Should().Contain("The available roles are:");
                rolePlayPrompt.Should().Contain("Alice,Bob");
                rolePlayPrompt.Should().Contain("From Alice:");
                option.StopSequence.Should().BeEquivalentTo([":"]);
                option.Temperature.Should().Be(0);
                option.MaxToken.Should().Be(128);
                option.Functions.Should().BeNull();
            })
            .ReturnsAsync(new TextMessage(Role.Assistant, "From Alice"));

        var alice = new EchoAgent("Alice");
        var bob = new EchoAgent("Bob");

        var orchestrator = new RolePlayOrchestrator(admin);
        var context = new OrchestrationContext
        {
            Candidates = [alice, bob],
            ChatHistory = [],
        };

        var speaker = await orchestrator.GetNextSpeakerAsync(context);
        speaker.Should().Be(alice);
    }

    [Fact]
    public async Task ItReturnNullWhenNoCandidateIsAvailableAsync()
    {
        var admin = Mock.Of<IAgent>();
        var orchestrator = new RolePlayOrchestrator(admin);
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
        var admin = Mock.Of<IAgent>();
        var alice = new EchoAgent("Alice");
        var orchestrator = new RolePlayOrchestrator(admin);
        var context = new OrchestrationContext
        {
            Candidates = [alice],
            ChatHistory = [],
        };

        var speaker = await orchestrator.GetNextSpeakerAsync(context);
        speaker.Should().Be(alice);
    }

    [Fact]
    public async Task ItThrowExceptionWhenAdminFailsToFollowPromptAsync()
    {
        var admin = Mock.Of<IAgent>();
        Mock.Get(admin).Setup(x => x.Name).Returns("Admin");
        Mock.Get(admin).Setup(x => x.GenerateReplyAsync(
            It.IsAny<IEnumerable<IMessage>>(),
            It.IsAny<GenerateReplyOptions>(),
            It.IsAny<CancellationToken>()))
            .ReturnsAsync(new TextMessage(Role.Assistant, "I don't know")); // admin fails to follow the prompt and returns an invalid message

        var alice = new EchoAgent("Alice");
        var bob = new EchoAgent("Bob");

        var orchestrator = new RolePlayOrchestrator(admin);
        var context = new OrchestrationContext
        {
            Candidates = [alice, bob],
            ChatHistory = [],
        };

        var action = async () => await orchestrator.GetNextSpeakerAsync(context);

        await action.Should().ThrowAsync<Exception>()
            .WithMessage("The response from admin is 't know, which is either not in the candidates list or not in the correct format.");
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

        var admin = Mock.Of<IAgent>();
        var orchestrator = new RolePlayOrchestrator(admin, workflow);
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

        var admin = Mock.Of<IAgent>();
        var orchestrator = new RolePlayOrchestrator(admin, workflow);
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

    [Fact]
    public async Task ItUseCandidatesFromWorflowAsync()
    {
        var workflow = new Graph();
        var alice = new EchoAgent("Alice");
        var bob = new EchoAgent("Bob");
        var charlie = new EchoAgent("Charlie");
        workflow.AddTransition(Transition.Create(alice, bob));
        workflow.AddTransition(Transition.Create(alice, charlie));

        var admin = Mock.Of<IAgent>();
        Mock.Get(admin).Setup(x => x.GenerateReplyAsync(
            It.IsAny<IEnumerable<IMessage>>(),
            It.IsAny<GenerateReplyOptions>(),
            It.IsAny<CancellationToken>()))
            .Callback<IEnumerable<IMessage>, GenerateReplyOptions, CancellationToken>((messages, option, _) =>
            {
                messages.First().IsSystemMessage().Should().BeTrue();

                // verify prompt
                var rolePlayPrompt = messages.First().GetContent();
                rolePlayPrompt.Should().Contain("Bob,Charlie");
                rolePlayPrompt.Should().Contain("From Bob:");
                option.StopSequence.Should().BeEquivalentTo([":"]);
                option.Temperature.Should().Be(0);
                option.MaxToken.Should().Be(128);
                option.Functions.Should().BeEmpty();
            })
            .ReturnsAsync(new TextMessage(Role.Assistant, "From Bob"));
        var orchestrator = new RolePlayOrchestrator(admin, workflow);
        var context = new OrchestrationContext
        {
            Candidates = [alice, bob],
            ChatHistory =
            [
                new TextMessage(Role.User, "Hello, Bob", from: "Alice"),
            ],
        };

        var speaker = await orchestrator.GetNextSpeakerAsync(context);
        speaker.Should().Be(bob);
    }

    [ApiKeyFact("OPENAI_API_KEY")]
    public async Task GPT_4o_CoderReviewerRunnerTestAsync()
    {
        var apiKey = Environment.GetEnvironmentVariable("OPENAI_API_KEY") ?? throw new InvalidOperationException("OPENAI_API_KEY is not set");
        var model = "gpt-4o";
        var openaiClient = new OpenAIClient(apiKey);
        var openAIChatAgent = new OpenAIChatAgent(
            chatClient: openaiClient.GetChatClient(model),
            name: "assistant")
            .RegisterMessageConnector();

        await CoderReviewerRunnerTestAsync(openAIChatAgent);
    }

    [ApiKeyFact("OPENAI_API_KEY")]
    public async Task GPT_4o_mini_CoderReviewerRunnerTestAsync()
    {
        var apiKey = Environment.GetEnvironmentVariable("OPENAI_API_KEY") ?? throw new InvalidOperationException("OPENAI_API_KEY is not set");
        var model = "gpt-4o-mini";
        var openaiClient = new OpenAIClient(apiKey);
        var openAIChatAgent = new OpenAIChatAgent(
            chatClient: openaiClient.GetChatClient(model),
            name: "assistant")
            .RegisterMessageConnector();

        await CoderReviewerRunnerTestAsync(openAIChatAgent);
    }

    [ApiKeyFact("GOOGLE_GEMINI_API_KEY")]
    public async Task GoogleGemini_1_5_flash_001_CoderReviewerRunnerTestAsync()
    {
        var apiKey = Environment.GetEnvironmentVariable("GOOGLE_GEMINI_API_KEY") ?? throw new InvalidOperationException("GOOGLE_GEMINI_API_KEY is not set");
        var geminiAgent = new GeminiChatAgent(
                name: "gemini",
                model: "gemini-1.5-flash-001",
                apiKey: apiKey)
            .RegisterMessageConnector();

        await CoderReviewerRunnerTestAsync(geminiAgent);
    }

    [ApiKeyFact("ANTHROPIC_API_KEY")]
    public async Task Claude3_Haiku_CoderReviewerRunnerTestAsync()
    {
        var apiKey = Environment.GetEnvironmentVariable("ANTHROPIC_API_KEY") ?? throw new Exception("Please set ANTHROPIC_API_KEY environment variable.");
        var client = new AnthropicClient(new HttpClient(), AnthropicConstants.Endpoint, apiKey);

        var agent = new AnthropicClientAgent(
            client,
            name: "AnthropicAgent",
            AnthropicConstants.Claude3Haiku,
            systemMessage: "You are a helpful AI assistant that convert user message to upper case")
            .RegisterMessageConnector();

        await CoderReviewerRunnerTestAsync(agent);
    }

    [ApiKeyFact("MISTRAL_API_KEY")]
    public async Task Mistra_7b_CoderReviewerRunnerTestAsync()
    {
        var apiKey = Environment.GetEnvironmentVariable("MISTRAL_API_KEY") ?? throw new InvalidOperationException("MISTRAL_API_KEY is not set.");
        var client = new MistralClient(apiKey: apiKey);

        var agent = new MistralClientAgent(
            client: client,
            name: "MistralClientAgent",
            model: "open-mistral-7b")
            .RegisterMessageConnector();

        await CoderReviewerRunnerTestAsync(agent);
    }

    [ApiKeyFact("GH_API_KEY")]
    public async Task LLaMA_3_1_CoderReviewerRunnerTestAsync()
    {
        var apiKey = Environment.GetEnvironmentVariable("GH_API_KEY") ?? throw new InvalidOperationException("GH_API_KEY is not set.");
        var endPoint = "https://models.github.ai/inference";

        var chatCompletionClient = new ChatCompletionsClient(new Uri(endPoint), new Azure.AzureKeyCredential(apiKey));
        var agent = new ChatCompletionsClientAgent(
            chatCompletionsClient: chatCompletionClient,
            name: "assistant",
            modelName: "Meta-Llama-3.1-70B-Instruct")
            .RegisterMessageConnector();

        await CoderReviewerRunnerTestAsync(agent);
    }

    /// <summary>
    /// This test is to mimic the conversation among coder, reviewer and runner.
    /// The coder will write the code, the reviewer will review the code, and the runner will run the code.
    /// </summary>
    /// <param name="admin"></param>
    /// <returns></returns>
    public async Task CoderReviewerRunnerTestAsync(IAgent admin)
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

        var orchestrator = new RolePlayOrchestrator(admin);
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
