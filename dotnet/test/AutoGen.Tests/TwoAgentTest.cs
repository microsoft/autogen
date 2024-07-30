// Copyright (c) Microsoft Corporation. All rights reserved.
// TwoAgentTest.cs
#pragma warning disable xUnit1013
using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using AutoGen.OpenAI;
using FluentAssertions;
using Xunit.Abstractions;

namespace AutoGen.Tests;

public partial class TwoAgentTest
{
    private ITestOutputHelper _output;
    public TwoAgentTest(ITestOutputHelper output)
    {
        _output = output;
    }

    [Function]
    public async Task<string> GetWeather(string city)
    {
        return $"[GetWeatherFunction] The weather in {city} is sunny";
    }

    [ApiKeyFact("AZURE_OPENAI_API_KEY", "AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_DEPLOY_NAME")]
    public async Task TwoAgentWeatherChatTestAsync()
    {
        var key = Environment.GetEnvironmentVariable("AZURE_OPENAI_API_KEY") ?? throw new ArgumentException("AZURE_OPENAI_API_KEY is not set");
        var endpoint = Environment.GetEnvironmentVariable("AZURE_OPENAI_ENDPOINT") ?? throw new ArgumentException("AZURE_OPENAI_ENDPOINT is not set");
        var deploymentName = Environment.GetEnvironmentVariable("AZURE_OPENAI_DEPLOY_NAME") ?? throw new ArgumentException("AZURE_OPENAI_DEPLOY_NAME is not set");
        var config = new AzureOpenAIConfig(endpoint, deploymentName, key);

        var assistant = new AssistantAgent(
            "assistant",
            llmConfig: new ConversableAgentConfig
            {
                ConfigList = new[] { config },
                FunctionContracts = new[]
                {
                    this.GetWeatherFunctionContract,
                },
            })
            .RegisterMiddleware(async (msgs, option, agent, ct) =>
            {
                var reply = await agent.GenerateReplyAsync(msgs, option, ct);
                var format = reply.FormatMessage();
                _output.WriteLine(format);

                return reply;
            });

        var user = new UserProxyAgent(
            name: "user",
            functionMap: new Dictionary<string, Func<string, Task<string>>>
            {
                { this.GetWeatherFunctionContract.Name, this.GetWeatherWrapper },
            })
            .RegisterMiddleware(async (msgs, option, agent, ct) =>
            {
                var lastMessage = msgs.Last();
                if (lastMessage.GetToolCalls()?.FirstOrDefault()?.FunctionName != null)
                {
                    return await agent.GenerateReplyAsync(msgs, option, ct);
                }
                else
                {
                    // terminate message
                    return new TextMessage(Role.Assistant, GroupChatExtension.TERMINATE);
                }
            })
            .RegisterMiddleware(async (msgs, option, agent, ct) =>
            {
                var reply = await agent.GenerateReplyAsync(msgs, option, ct);
                var format = reply.FormatMessage();
                _output.WriteLine(format);

                return reply;
            });

        var chatHistory = (await user.InitiateChatAsync(assistant, "what's weather in New York", 10)).ToArray();

        // the last message should be terminated message
        chatHistory.Last().IsGroupChatTerminateMessage().Should().BeTrue();

        // the third last message should be the weather message from function
        chatHistory[^3].GetContent().Should().Be("[GetWeatherFunction] The weather in New York is sunny");

        // the # of messages should be 5
        chatHistory.Length.Should().Be(5);
    }

    public async Task TwoAgentGetWeatherFunctionCallTestAsync(IAgent user, IAgent assistant)
    {
        var question = new TextMessage(Role.Assistant, "what's the weather in Seattle", from: user.Name);
        var assistantReply = await assistant.SendAsync(question);
        assistantReply.Should().BeOfType<ToolCallMessage>();
        var toolCallResult = await user.SendAsync(chatHistory: [question, assistantReply]);
        toolCallResult.Should().BeOfType<ToolCallResultMessage>();
        var finalReply = await assistant.SendAsync(chatHistory: [question, assistantReply, toolCallResult]);
        finalReply.Should().BeOfType<TextMessage>();
        finalReply.GetContent()!.ToLower().Should().Contain("sunny");
    }
}
