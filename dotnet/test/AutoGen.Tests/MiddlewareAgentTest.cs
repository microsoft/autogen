// Copyright (c) Microsoft Corporation. All rights reserved.
// MiddlewareAgentTest.cs

using System.Linq;
using System.Threading.Tasks;
using FluentAssertions;
using Xunit;

namespace AutoGen.Tests;

public class MiddlewareAgentTest
{
    [Fact]
    public async Task MiddlewareAgentUseTestAsync()
    {
        IAgent echoAgent = new EchoAgent("echo");

        var middlewareAgent = new MiddlewareAgent(echoAgent);

        // no middleware added
        // the reply should be the same as the original agent
        middlewareAgent.Name.Should().Be("echo");
        var reply = await middlewareAgent.SendAsync("hello");
        reply.GetContent().Should().Be("hello");

        middlewareAgent.Use(async (messages, options, agent, ct) =>
        {
            var lastMessage = messages.Last() as TextMessage;
            lastMessage!.Content = $"[middleware 0] {lastMessage.Content}";
            return await agent.GenerateReplyAsync(messages, options, ct);
        });

        reply = await middlewareAgent.SendAsync("hello");
        reply.GetContent().Should().Be("[middleware 0] hello");

        middlewareAgent.Use(async (messages, options, agent, ct) =>
        {
            var lastMessage = messages.Last() as TextMessage;
            lastMessage!.Content = $"[middleware 1] {lastMessage.Content}";
            return await agent.GenerateReplyAsync(messages, options, ct);
        });

        // when multiple middleware are added, they will be executed in LIFO order
        reply = await middlewareAgent.SendAsync("hello");
        reply.GetContent().Should().Be("[middleware 0] [middleware 1] hello");

        // test short cut
        // short cut middleware will not call next middleware
        middlewareAgent.Use(async (messages, options, next, ct) =>
        {
            var lastMessage = messages.Last() as TextMessage;
            lastMessage!.Content = $"[middleware shortcut] {lastMessage.Content}";
            return lastMessage;
        });
        reply = await middlewareAgent.SendAsync("hello");
        reply.GetContent().Should().Be("[middleware shortcut] hello");
    }

    [Fact]
    public async Task RegisterMiddlewareTestAsync()
    {
        var echoAgent = new EchoAgent("echo");

        // RegisterMiddleware will return a new agent and keep the original agent unchanged
        var middlewareAgent = echoAgent.RegisterMiddleware(async (messages, options, agent, ct) =>
        {
            var lastMessage = messages.Last() as TextMessage;
            lastMessage!.Content = $"[middleware 0] {lastMessage.Content}";
            return await agent.GenerateReplyAsync(messages, options, ct);
        });

        middlewareAgent.Should().BeOfType<MiddlewareAgent<EchoAgent>>();
        middlewareAgent.Middlewares.Count().Should().Be(1);
        var reply = await middlewareAgent.SendAsync("hello");
        reply.GetContent().Should().Be("[middleware 0] hello");
        reply = await echoAgent.SendAsync("hello");
        reply.GetContent().Should().Be("hello");

        // when multiple middleware are added, they will be executed in LIFO order
        middlewareAgent = middlewareAgent.RegisterMiddleware(async (messages, options, agent, ct) =>
        {
            var lastMessage = messages.Last() as TextMessage;
            lastMessage!.Content = $"[middleware 1] {lastMessage.Content}";
            return await agent.GenerateReplyAsync(messages, options, ct);
        });

        middlewareAgent.Middlewares.Count().Should().Be(2);
        reply = await middlewareAgent.SendAsync("hello");
        reply.GetContent().Should().Be("[middleware 0] [middleware 1] hello");

        // test short cut
        // short cut middleware will not call next middleware
        middlewareAgent = middlewareAgent.RegisterMiddleware(async (messages, options, agent, ct) =>
        {
            var lastMessage = messages.Last() as TextMessage;
            lastMessage!.Content = $"[middleware shortcut] {lastMessage.Content}";
            return lastMessage;
        });

        reply = await middlewareAgent.SendAsync("hello");
        reply.GetContent().Should().Be("[middleware shortcut] hello");

        middlewareAgent.Middlewares.Count().Should().Be(3);
    }
}
