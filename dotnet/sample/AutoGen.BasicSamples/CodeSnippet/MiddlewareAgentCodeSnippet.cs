// Copyright (c) Microsoft Corporation. All rights reserved.
// MiddlewareAgentCodeSnippet.cs

using System.Text.Json;
using AutoGen.Core;
using AutoGen.OpenAI;
using FluentAssertions;

namespace AutoGen.BasicSample.CodeSnippet;

public class MiddlewareAgentCodeSnippet
{
    public async Task CreateMiddlewareAgentAsync()
    {
        #region create_middleware_agent_with_original_agent
        // Create an agent that always replies "Hi!"
        IAgent agent = new DefaultReplyAgent(name: "assistant", defaultReply: "Hi!");

        // Create a middleware agent on top of default reply agent
        var middlewareAgent = new MiddlewareAgent(innerAgent: agent);
        middlewareAgent.Use(async (messages, options, agent, ct) =>
        {
            if (messages.Last() is TextMessage lastMessage && lastMessage.Content.Contains("Hello World"))
            {
                lastMessage.Content = $"[middleware 0] {lastMessage.Content}";
                return lastMessage;
            }

            return await agent.GenerateReplyAsync(messages, options, ct);
        });

        var reply = await middlewareAgent.SendAsync("Hello World");
        reply.GetContent().Should().Be("[middleware 0] Hello World");
        reply = await middlewareAgent.SendAsync("Hello AI!");
        reply.GetContent().Should().Be("Hi!");
        #endregion create_middleware_agent_with_original_agent

        #region register_middleware_agent
        middlewareAgent = agent.RegisterMiddleware(async (messages, options, agent, ct) =>
        {
            if (messages.Last() is TextMessage lastMessage && lastMessage.Content.Contains("Hello World"))
            {
                lastMessage.Content = $"[middleware 0] {lastMessage.Content}";
                return lastMessage;
            }

            return await agent.GenerateReplyAsync(messages, options, ct);
        });
        #endregion register_middleware_agent

        #region short_circuit_middleware_agent
        // This middleware will short circuit the agent and return a message directly.
        middlewareAgent.Use(async (messages, options, agent, ct) =>
        {
            return new TextMessage(Role.Assistant, $"[middleware shortcut]");
        });
        #endregion short_circuit_middleware_agent
    }

    public async Task RegisterStreamingMiddlewareAsync()
    {
        IStreamingAgent streamingAgent = default;
        #region register_streaming_middleware
        var connector = new OpenAIChatRequestMessageConnector();
        var agent = streamingAgent!
                .RegisterStreamingMiddleware(connector);
        #endregion register_streaming_middleware
    }

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
        reply.GetContent().Should().Be("Hello World");
        #endregion code_snippet_1

        #region code_snippet_2
        middlewareAgent.Use(async (messages, options, agent, ct) =>
        {
            var lastMessage = messages.Last() as TextMessage;
            lastMessage.Content = $"[middleware 0] {lastMessage.Content}";
            return await agent.GenerateReplyAsync(messages, options, ct);
        });

        reply = await middlewareAgent.SendAsync("Hello World");
        reply.Should().BeOfType<TextMessage>();
        var textReply = (TextMessage)reply;
        textReply.Content.Should().Be("[middleware 0] Hello World");
        #endregion code_snippet_2
        #region code_snippet_2_1
        middlewareAgent = agent.RegisterMiddleware(async (messages, options, agnet, ct) =>
        {
            var lastMessage = messages.Last() as TextMessage;
            lastMessage.Content = $"[middleware 0] {lastMessage.Content}";
            return await agent.GenerateReplyAsync(messages, options, ct);
        });

        reply = await middlewareAgent.SendAsync("Hello World");
        reply.GetContent().Should().Be("[middleware 0] Hello World");
        #endregion code_snippet_2_1
        #region code_snippet_3
        middlewareAgent.Use(async (messages, options, agent, ct) =>
        {
            var lastMessage = messages.Last() as TextMessage;
            lastMessage.Content = $"[middleware 1] {lastMessage.Content}";
            return await agent.GenerateReplyAsync(messages, options, ct);
        });

        reply = await middlewareAgent.SendAsync("Hello World");
        reply.GetContent().Should().Be("[middleware 0] [middleware 1] Hello World");
        #endregion code_snippet_3

        #region code_snippet_4
        middlewareAgent.Use(async (messages, options, next, ct) =>
        {
            var lastMessage = messages.Last() as TextMessage;
            lastMessage.Content = $"[middleware shortcut]";

            return lastMessage;
        });

        reply = await middlewareAgent.SendAsync("Hello World");
        reply.GetContent().Should().Be("[middleware shortcut]");
        #endregion code_snippet_4

        #region retrieve_inner_agent
        var innerAgent = middlewareAgent.Agent;
        #endregion retrieve_inner_agent

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
        var jsonAgent = middlewareAgent.RegisterMiddleware(async (messages, options, agent, ct) =>
        {
            var maxAttempt = 5;
            var reply = await agent.GenerateReplyAsync(messages, options, ct);
            while (maxAttempt-- > 0)
            {
                if (JsonSerializer.Deserialize<Dictionary<string, object>>(reply.GetContent()) is { } dict)
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

            throw new Exception("agent fails to generate json response");
        });
        #endregion code_snippet_response_format_forcement
    }
}
