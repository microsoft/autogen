// Copyright (c) Microsoft Corporation. All rights reserved.
// MiddlewareAgentCodeSnippet.cs

using System.Text.Json;
using FluentAssertions;

namespace AutoGen.BasicSample.CodeSnippet;

public class MiddlewareAgentCodeSnippet
{
    public async Task CodeSnippet1()
    {
        #region code_snippet_1
        // Create an agent that always replies "Hello World"
        IAgent agent = new DefaultReplyAgent(name: "assistant", defaultReply: "Hello World");

        // Create a middleware agent on top of default reply agent
        var middlewareAgent = new MiddlewareAgent(innerAgent: agent);

        // Since no middleware is added, middlewareAgent will simply proxy into the inner agent to generate reply.
        var reply = await middlewareAgent.SendAsync("Hello World");
        reply.From.Should().Be("assistant");
        reply.Content.Should().Be("Hello World");
        #endregion code_snippet_1

        #region code_snippet_2
        middlewareAgent.Use(async (messages, options, next, ct) =>
        {
            var lastMessage = messages.Last();
            lastMessage.Content = $"[middleware 0] {lastMessage.Content}";
            return await next(messages, options, ct);
        });

        reply = await middlewareAgent.SendAsync("Hello World");
        reply.Content.Should().Be("[middleware 0] Hello World");
        #endregion code_snippet_2
        #region code_snippet_3
        middlewareAgent.Use(async (messages, options, next, ct) =>
        {
            var lastMessage = messages.Last();
            lastMessage.Content = $"[middleware 1] {lastMessage.Content}";
            return await next(messages, options, ct);
        });

        reply = await middlewareAgent.SendAsync("Hello World");
        reply.Content.Should().Be("[middleware 0] [middleware 1] Hello World");
        #endregion code_snippet_3

        #region code_snippet_4
        middlewareAgent.Use(async (messages, options, next, ct) =>
        {
            var lastMessage = messages.Last();
            lastMessage.Content = $"[middleware shortcut]";
        });

        reply = await middlewareAgent.SendAsync("Hello World");
        reply.Content.Should().Be("[middleware shortcut]");
        #endregion code_snippet_4

        #region code_snippet_logging_to_console
        var agentWithLogging = middlewareAgent.RegisterMiddleware(async (messages, options, agent, ct) =>
        {
            var reply = await agent.GenerateReplyAsync(messages, options, ct);
            var formattedMessage = reply.FormatMessage();
            Console.WriteLine(formattedMessage);

            return reply;
        });
        #endregion code_snippet_logging_to_console

        #region code_snippet_response_format_forcement
        var functionCallAgent = middlewareAgent.RegisterMiddleware(async (messages, options, agent, ct) =>
        {
            var maxAttempt = 5;
            var reply = await agent.GenerateReplyAsync(messages, options, ct);
            while (maxAttempt-- > 0)
            {
                if (JsonSerializer.Deserialize<Dictionary<string, object>>(reply.Content) is { } dict)
                {
                    return reply;
                }
                else
                {
                    await Task.Delay(1000);
                    var reviewPrompt = @"The format is not json, please modify your response to json format
-- ORIGINAL MESSAGE --
{reply.Content}
-- END OF ORIGINAL MESSAGE --

Reply again with json format.";
                    reply = await agent.SendAsync(reviewPrompt, messages, ct);
                }
            }

            return reply;
        });
        #endregion code_snippet_response_format_forcement
    }
}
