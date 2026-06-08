// Copyright (c) Microsoft Corporation. All rights reserved.
// Agent_Middleware.cs

#region Using
using AutoGen.Core;
using AutoGen.OpenAI;
using AutoGen.OpenAI.Extension;
#endregion Using
using FluentAssertions;
using OpenAI.Chat;

namespace AutoGen.Basic.Sample;

public class Agent_Middleware
{
    public static async Task RunTokenCountAsync()
    {
        #region Create_Agent
        var gpt4o = LLMConfiguration.GetOpenAIGPT4o_mini();
        var openaiMessageConnector = new OpenAIChatRequestMessageConnector();
        var totalTokenCount = 0;
        var agent = new OpenAIChatAgent(
            chatClient: gpt4o,
            name: "agent",
            systemMessage: "You are a helpful AI assistant")
            .RegisterMiddleware(async (messages, option, innerAgent, ct) =>
            {
                var reply = await innerAgent.GenerateReplyAsync(messages, option, ct);
                if (reply is MessageEnvelope<ChatCompletion> chatCompletions)
                {
                    var tokenCount = chatCompletions.Content.Usage.TotalTokenCount;
                    totalTokenCount += tokenCount;
                }
                return reply;
            })
            .RegisterMiddleware(openaiMessageConnector);
        #endregion Create_Agent

        #region Chat_With_Agent
        var reply = await agent.SendAsync("Tell me a joke");
        Console.WriteLine($"Total token count: {totalTokenCount}");
        #endregion Chat_With_Agent

        #region verify_reply
        reply.Should().BeOfType<TextMessage>();
        totalTokenCount.Should().BeGreaterThan(0);
        #endregion verify_reply
    }

    public static async Task RunRagTaskAsync()
    {
        #region Create_Agent
        var gpt4o = LLMConfiguration.GetOpenAIGPT4o_mini();
        var agent = new OpenAIChatAgent(
            chatClient: gpt4o,
            name: "agent",
            systemMessage: "You are a helpful AI assistant")
            .RegisterMessageConnector()
            .RegisterMiddleware(async (messages, option, innerAgent, ct) =>
            {
                var today = DateTime.UtcNow;
                var todayMessage = new TextMessage(Role.System, $"Today is {today:yyyy-MM-dd}");
                messages = messages.Concat([todayMessage]);
                return await innerAgent.GenerateReplyAsync(messages, option, ct);
            })
            .RegisterPrintMessage();
        #endregion Create_Agent

        #region Chat_With_Agent
        var reply = await agent.SendAsync("what's the date today");
        #endregion Chat_With_Agent
    }
}
