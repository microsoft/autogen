// Copyright (c) Microsoft Corporation. All rights reserved.
// FunctionCallMiddlewareStreamingTests.cs

using System.Collections.Generic;
using System.Runtime.CompilerServices;
using System.Threading;
using System.Threading.Tasks;
using FluentAssertions;
using Xunit;

namespace AutoGen.Tests;

[Trait("Category", "UnitV1")]
public class FunctionCallMiddlewareStreamingTests
{
    [Theory]
    [InlineData("echo", "tool result")]
    [InlineData("missing", "Function missing is not available. Available functions are: echo")]
    public async Task IncomingToolCallsDoNotInvokeTheStreamingAgentAsync(string functionName, string expectedContent)
    {
        var agent = new StreamingProbeAgent();
        var toolCalls = 0;
        var middleware = new FunctionCallMiddleware(
            functionMap: new Dictionary<string, System.Func<string, Task<string>>>
            {
                ["echo"] = _ =>
                {
                    toolCalls++;
                    return Task.FromResult("tool result");
                },
            });
        var toolCall = new ToolCall(functionName, "{}") { ToolCallId = "call-1" };
        var context = new MiddlewareContext([new ToolCallMessage([toolCall], from: "user")], options: null);
        var messages = new List<IMessage>();

        await foreach (var message in middleware.InvokeAsync(context, agent))
        {
            messages.Add(message);
        }

        messages.Should().ContainSingle()
            .Which.Should().BeOfType<ToolCallResultMessage>()
            .Which.ToolCalls.Should().ContainSingle()
            .Which.ToolCallId.Should().Be("call-1");
        messages[0].GetContent().Should().Be(expectedContent);
        toolCalls.Should().Be(functionName == "echo" ? 1 : 0);
        agent.StreamingCalls.Should().Be(0);
    }

    [Fact]
    public async Task OrdinaryMessagesStillInvokeTheStreamingAgentAsync()
    {
        var agent = new StreamingProbeAgent();
        var middleware = new FunctionCallMiddleware();
        var context = new MiddlewareContext([new TextMessage(Role.User, "hello")], options: null);
        var messages = new List<IMessage>();

        await foreach (var message in middleware.InvokeAsync(context, agent))
        {
            messages.Add(message);
        }

        messages.Should().ContainSingle().Which.GetContent().Should().Be("agent response");
        agent.StreamingCalls.Should().Be(1);
    }

    private sealed class StreamingProbeAgent : IStreamingAgent
    {
        public string Name => "probe";

        public int StreamingCalls { get; private set; }

        public Task<IMessage> GenerateReplyAsync(
            IEnumerable<IMessage> messages,
            GenerateReplyOptions? options = null,
            CancellationToken cancellationToken = default)
        {
            return Task.FromResult<IMessage>(new TextMessage(Role.Assistant, "agent response", Name));
        }

        public async IAsyncEnumerable<IMessage> GenerateStreamingReplyAsync(
            IEnumerable<IMessage> messages,
            GenerateReplyOptions? options = null,
            [EnumeratorCancellation] CancellationToken cancellationToken = default)
        {
            await Task.CompletedTask;
            cancellationToken.ThrowIfCancellationRequested();
            StreamingCalls++;
            yield return new TextMessage(Role.Assistant, "agent response", Name);
        }
    }
}
