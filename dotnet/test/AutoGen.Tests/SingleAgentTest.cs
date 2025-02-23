// Copyright (c) Microsoft Corporation. All rights reserved.
// SingleAgentTest.cs

using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using FluentAssertions;
using Xunit;
using Xunit.Abstractions;

namespace AutoGen.Tests;

[Trait("Category", "UnitV1")]
public partial class SingleAgentTest
{
    private ITestOutputHelper _output;
    public SingleAgentTest(ITestOutputHelper output)
    {
        _output = output;
    }

    private ILLMConfig CreateAzureOpenAIGPT35TurboConfig()
    {
        var key = Environment.GetEnvironmentVariable("AZURE_OPENAI_API_KEY") ?? throw new ArgumentException("AZURE_OPENAI_API_KEY is not set");
        var endpoint = Environment.GetEnvironmentVariable("AZURE_OPENAI_ENDPOINT") ?? throw new ArgumentException("AZURE_OPENAI_ENDPOINT is not set");
        var deployName = Environment.GetEnvironmentVariable("AZURE_OPENAI_DEPLOY_NAME") ?? throw new ArgumentException("AZURE_OPENAI_DEPLOY_NAME is not set");
        return new AzureOpenAIConfig(endpoint, deployName, key);
    }

    private ILLMConfig CreateOpenAIGPT4VisionConfig()
    {
        var key = Environment.GetEnvironmentVariable("OPENAI_API_KEY") ?? throw new ArgumentException("OPENAI_API_KEY is not set");
        return new OpenAIConfig(key, "gpt-4-vision-preview");
    }

    [ApiKeyFact("AZURE_OPENAI_API_KEY", "AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_DEPLOY_NAME")]
    public async Task AssistantAgentFunctionCallTestAsync()
    {
        var config = this.CreateAzureOpenAIGPT35TurboConfig();

        var llmConfig = new ConversableAgentConfig
        {
            Temperature = 0,
            FunctionContracts = new[]
            {
                this.EchoAsyncFunctionContract,
            },
            ConfigList = new[]
            {
                config,
            },
        };

        var assistantAgent = new AssistantAgent(
            name: "assistant",
            llmConfig: llmConfig);

        await EchoFunctionCallTestAsync(assistantAgent);
    }

    [Fact]
    public async Task AssistantAgentDefaultReplyTestAsync()
    {
        var assistantAgent = new AssistantAgent(
            llmConfig: null,
            name: "assistant",
            defaultReply: "hello world");

        var reply = await assistantAgent.SendAsync("hi");

        reply.GetContent().Should().Be("hello world");
        reply.GetRole().Should().Be(Role.Assistant);
        reply.From.Should().Be(assistantAgent.Name);
    }

    [ApiKeyFact("AZURE_OPENAI_API_KEY", "AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_DEPLOY_NAME")]
    public async Task AssistantAgentFunctionCallSelfExecutionTestAsync()
    {
        var config = this.CreateAzureOpenAIGPT35TurboConfig();
        var llmConfig = new ConversableAgentConfig
        {
            FunctionContracts = new[]
            {
                this.EchoAsyncFunctionContract,
            },
            ConfigList = new[]
            {
                config,
            },
        };
        var assistantAgent = new AssistantAgent(
            name: "assistant",
            llmConfig: llmConfig,
            functionMap: new Dictionary<string, Func<string, Task<string>>>
            {
                { nameof(EchoAsync), this.EchoAsyncWrapper },
            });

        await EchoFunctionCallExecutionTestAsync(assistantAgent);
    }

    /// <summary>
    /// echo when asked.
    /// </summary>
    /// <param name="message">message to echo</param>
    [FunctionAttribute]
    public async Task<string> EchoAsync(string message)
    {
        return $"[ECHO] {message}";
    }

    /// <summary>
    /// return the label name with hightest inference cost
    /// </summary>
    /// <param name="labelName"></param>
    /// <returns></returns>
    [FunctionAttribute]
    public async Task<string> GetHighestLabel(string labelName, string color)
    {
        return $"[HIGHEST_LABEL] {labelName} {color}";
    }

    public async Task EchoFunctionCallTestAsync(IAgent agent)
    {
        //var message = new TextMessage(Role.System, "You are a helpful AI assistant that call echo function");
        var helloWorld = new TextMessage(Role.User, "echo Hello world");

        var reply = await agent.SendAsync(chatHistory: new[] { helloWorld });

        reply.From.Should().Be(agent.Name);
        reply.GetToolCalls()!.First().FunctionName.Should().Be(nameof(EchoAsync));
    }

    public async Task EchoFunctionCallExecutionTestAsync(IAgent agent)
    {
        //var message = new TextMessage(Role.System, "You are a helpful AI assistant that echo whatever user says");
        var helloWorld = new TextMessage(Role.User, "echo Hello world");

        var reply = await agent.SendAsync(chatHistory: new[] { helloWorld });

        reply.GetContent().Should().Be("[ECHO] Hello world");
        reply.From.Should().Be(agent.Name);
        reply.Should().BeOfType<ToolCallAggregateMessage>();
    }

    public async Task EchoFunctionCallExecutionStreamingTestAsync(IStreamingAgent agent)
    {
        //var message = new TextMessage(Role.System, "You are a helpful AI assistant that echo whatever user says");
        var helloWorld = new TextMessage(Role.User, "echo Hello world");
        var option = new GenerateReplyOptions
        {
            Temperature = 0,
        };
        var replyStream = agent.GenerateStreamingReplyAsync(messages: new[] { helloWorld }, option);
        var answer = "[ECHO] Hello world";
        IMessage? finalReply = default;
        await foreach (var reply in replyStream)
        {
            reply.From.Should().Be(agent.Name);
            finalReply = reply;
        }

        if (finalReply is ToolCallAggregateMessage aggregateMessage)
        {
            var toolCallResultMessage = aggregateMessage.Message2;
            toolCallResultMessage.ToolCalls.First().Result.Should().Be(answer);
            toolCallResultMessage.From.Should().Be(agent.Name);
            toolCallResultMessage.ToolCalls.First().FunctionName.Should().Be(nameof(EchoAsync));
        }
        else
        {
            throw new Exception("unexpected message type");
        }
    }

    public async Task UpperCaseTestAsync(IAgent agent)
    {
        var message = new TextMessage(Role.User, "Please convert abcde to upper case.");

        var reply = await agent.SendAsync(chatHistory: new[] { message });

        reply.GetContent().Should().Contain("ABCDE");
        reply.From.Should().Be(agent.Name);
    }

    public async Task UpperCaseStreamingTestAsync(IStreamingAgent agent)
    {
        var message = new TextMessage(Role.User, "Please convert 'hello world' to upper case");
        var option = new GenerateReplyOptions
        {
            Temperature = 0,
        };
        var replyStream = agent.GenerateStreamingReplyAsync(messages: new[] { message }, option);
        var answer = "HELLO WORLD";
        TextMessage? finalReply = default;
        await foreach (var reply in replyStream)
        {
            if (reply is TextMessageUpdate update)
            {
                update.From.Should().Be(agent.Name);

                if (finalReply is null)
                {
                    finalReply = new TextMessage(update);
                }
                else
                {
                    finalReply.Update(update);
                }

                continue;
            }
            else if (reply is TextMessage textMessage)
            {
                finalReply = textMessage;
                continue;
            }

            throw new Exception("unexpected message type");
        }

        finalReply!.Content.Should().Contain(answer);
        finalReply!.Role.Should().Be(Role.Assistant);
        finalReply!.From.Should().Be(agent.Name);
    }
}
