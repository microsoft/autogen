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

[Trait("Category", "UnitV1")]
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

        await BusinessWorkflowTest(chatClient);
        await CoderReviewerRunnerTestAsync(chatClient);
    }

    [ApiKeyFact("OPENAI_API_KEY")]
    public async Task GPT_4o_CoderReviewerRunnerTestAsync()
    {
        var apiKey = Environment.GetEnvironmentVariable("OPENAI_API_KEY") ?? throw new InvalidOperationException("OPENAI_API_KEY is not set");
        var model = "gpt-4o";
        var openaiClient = new OpenAIClient(apiKey);
        var chatClient = openaiClient.GetChatClient(model);

        await BusinessWorkflowTest(chatClient);
        await CoderReviewerRunnerTestAsync(chatClient);
    }

    [ApiKeyFact("OPENAI_API_KEY")]
    public async Task GPT_4o_mini_CoderReviewerRunnerTestAsync()
    {
        var apiKey = Environment.GetEnvironmentVariable("OPENAI_API_KEY") ?? throw new InvalidOperationException("OPENAI_API_KEY is not set");
        var model = "gpt-4o-mini";
        var openaiClient = new OpenAIClient(apiKey);
        var chatClient = openaiClient.GetChatClient(model);

        await BusinessWorkflowTest(chatClient);
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

    // test if the tool call orchestrator still run business workflow when the conversation is not in English
    private async Task BusinessWorkflowTest(ChatClient client)
    {
        var ceo = new EchoAgent("乙方首席执行官");
        var pm = new EchoAgent("乙方项目经理");
        var dev = new EchoAgent("乙方开发人员");
        var user = new EchoAgent("甲方");
        var initializeMessage = new List<IMessage>
        {
            new TextMessage(Role.User, "你好，我是你们的甲方", from: user.Name),
            new TextMessage(Role.User, "你好，我是乙方首席执行官，我将负责对接甲方和给项目经理及开发人员分配任务", from: ceo.Name),
            new TextMessage(Role.User, "你好，我是乙方项目经理，我将负责项目的进度和质量", from: pm.Name),
            new TextMessage(Role.User, "你好，我是乙方开发人员 我将负责项目的具体开发", from: dev.Name),
            new TextMessage(Role.User, "开发一个淘宝，预算1W", from: user.Name),
        };

        var workflow = new Graph();
        workflow.AddTransition(Transition.Create(ceo, pm));
        workflow.AddTransition(Transition.Create(ceo, dev));
        workflow.AddTransition(Transition.Create(pm, ceo));
        workflow.AddTransition(Transition.Create(dev, ceo));
        workflow.AddTransition(Transition.Create(user, ceo));
        workflow.AddTransition(Transition.Create(ceo, user));

        var chatHistory = new List<IMessage>()
        {
            new TextMessage(Role.User, """
            项目经理，如何使用1W预算开发一个淘宝
            """, from: ceo.Name),
            new TextMessage(Role.User, """
            对于1万预算开发淘宝类网站,以下是关键建议:
            技术选择:
            - 使用开源电商系统节省成本, 选择便宜但稳定的云服务器和域名,预算2000元/年
            - 核心功能优先
            - 人员安排:
             - 找1位全栈开发,负责系统搭建(6000元)
             - 1位兼职UI设计(2000元)
            - 进度规划:
             - 基础功能1个月完成,后续根据运营情况逐步优化。
            """, from: pm.Name),
            new TextMessage(Role.User, "好的，开发人员，请根据项目经理的规划开始开发", from: ceo.Name),
            new TextMessage(Role.User, """
            好的，已开发完毕
            ```html
            <button class="taobao-button" onclick="window.location.href='https://www.taobao.com'">
                Visit Taobao
            </button>
            ```
            """, from: dev.Name),
            new TextMessage(Role.User, "好的，项目已完成，甲方请付款", from: ceo.Name),
        };

        var orchestrator = new RolePlayToolCallOrchestrator(client, workflow);

        foreach (var message in chatHistory)
        {
            var context = new OrchestrationContext
            {
                Candidates = [ceo, pm, dev, user],
                ChatHistory = initializeMessage,
            };

            var speaker = await orchestrator.GetNextSpeakerAsync(context);
            speaker!.Name.Should().Be(message.From);
            initializeMessage.Add(message);
        }

        // the last next speaker should be the user
        var lastSpeaker = await orchestrator.GetNextSpeakerAsync(new OrchestrationContext
        {
            Candidates = [ceo, pm, dev, user],
            ChatHistory = initializeMessage,
        });

        lastSpeaker!.Name.Should().Be(user.Name);
    }
}
