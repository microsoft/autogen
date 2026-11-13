// Copyright (c) Microsoft Corporation. All rights reserved.
// FunctionCallMiddlewareCancellationTests.cs

using System;
using System.Collections.Generic;
using System.Runtime.CompilerServices;
using System.Threading;
using System.Threading.Tasks;
using FluentAssertions;
using Microsoft.Extensions.AI;
using Xunit;

namespace AutoGen.Tests;

[Trait("Category", "UnitV1")]
public class FunctionCallMiddlewareCancellationTests
{
    [Theory]
    [InlineData(false, false)]
    [InlineData(false, true)]
    [InlineData(true, false)]
    [InlineData(true, true)]
    public async Task FunctionsReceiveTheCallerTokenAsync(bool streaming, bool incomingToolCall)
    {
        using var cancellation = new CancellationTokenSource();
        CancellationToken observedToken = default;
        Func<CancellationToken, string> function = token =>
        {
            observedToken = token;
            return "tool result";
        };
        var middleware = new FunctionCallMiddleware(new[] { AIFunctionFactory.Create(function, name: "probe") });

        await InvokeAsync(middleware, streaming, incomingToolCall, cancellation.Token);

        observedToken.Should().Be(cancellation.Token);
    }

    [Theory]
    [InlineData(false, false)]
    [InlineData(false, true)]
    [InlineData(true, false)]
    [InlineData(true, true)]
    public async Task InFlightFunctionsAreCancelledAsync(bool streaming, bool incomingToolCall)
    {
        using var cancellation = new CancellationTokenSource();
        var started = new TaskCompletionSource<bool>(TaskCreationOptions.RunContinuationsAsynchronously);
        Func<CancellationToken, Task<string>> function = async token =>
        {
            started.SetResult(true);
            await Task.Delay(Timeout.Infinite, token);
            return "unreachable";
        };
        var middleware = new FunctionCallMiddleware(new[] { AIFunctionFactory.Create(function, name: "probe") });
        var invocation = InvokeAsync(middleware, streaming, incomingToolCall, cancellation.Token);

        await started.Task.WaitAsync(TimeSpan.FromSeconds(10));
        cancellation.Cancel();

        Func<Task> complete = () => invocation.WaitAsync(TimeSpan.FromSeconds(10));
        await complete.Should().ThrowAsync<OperationCanceledException>();
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task CancelledRequestsDoNotStartFunctionsAsync(bool streaming)
    {
        using var cancellation = new CancellationTokenSource();
        cancellation.Cancel();
        var calls = 0;
        Func<string> function = () =>
        {
            calls++;
            return "unexpected";
        };
        var middleware = new FunctionCallMiddleware(new[] { AIFunctionFactory.Create(function, name: "probe") });

        Func<Task> invoke = () => InvokeAsync(middleware, streaming, incomingToolCall: true, cancellation.Token);
        await invoke.Should().ThrowAsync<OperationCanceledException>();

        calls.Should().Be(0);
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task CancellationPreventsFurtherLegacyFunctionCallsAsync(bool streaming)
    {
        using var cancellation = new CancellationTokenSource();
        var calls = 0;
        var middleware = new FunctionCallMiddleware(
            functionMap: new Dictionary<string, Func<string, Task<string>>>
            {
                ["probe"] = _ =>
                {
                    calls++;
                    cancellation.Cancel();
                    return Task.FromResult("tool result");
                },
            });
        var context = new MiddlewareContext(
            [new ToolCallMessage([new ToolCall("probe", "{}"), new ToolCall("probe", "{}")])],
            options: null);
        var agent = new ToolCallingAgent(replyWithToolCall: false);

        Func<Task> invoke = async () =>
        {
            if (streaming)
            {
                await foreach (var _ in middleware.InvokeAsync(context, agent, cancellation.Token))
                {
                }
            }
            else
            {
                await middleware.InvokeAsync(context, (IAgent)agent, cancellation.Token);
            }
        };
        await invoke.Should().ThrowAsync<OperationCanceledException>();

        calls.Should().Be(1);
    }

    [Fact]
    public async Task StreamedFunctionUpdatesPreserveCancellationAsync()
    {
        using var cancellation = new CancellationTokenSource();
        CancellationToken observedToken = default;
        Func<CancellationToken, string> function = token =>
        {
            observedToken = token;
            return "tool result";
        };
        var middleware = new FunctionCallMiddleware(new[] { AIFunctionFactory.Create(function, name: "probe") });
        var agent = new ToolCallingAgent(replyWithToolCall: true, useUpdates: true);
        var context = new MiddlewareContext([new TextMessage(Role.User, "call the tool")], options: null);
        var messages = new List<IMessage>();

        await foreach (var message in middleware.InvokeAsync(context, agent, cancellation.Token))
        {
            messages.Add(message);
        }

        messages.Should().ContainSingle().Which.Should().BeOfType<ToolCallAggregateMessage>();
        messages[0].GetContent().Should().Be("tool result");
        observedToken.Should().Be(cancellation.Token);
    }

    private static async Task InvokeAsync(
        FunctionCallMiddleware middleware,
        bool streaming,
        bool incomingToolCall,
        CancellationToken cancellationToken)
    {
        var agent = new ToolCallingAgent(replyWithToolCall: !incomingToolCall);
        IMessage input = incomingToolCall
            ? new ToolCallMessage("probe", "{}", from: "user")
            : new TextMessage(Role.User, "call the tool");
        var context = new MiddlewareContext([input], options: null);
        if (streaming)
        {
            await foreach (var _ in middleware.InvokeAsync(context, agent, cancellationToken))
            {
            }
        }
        else
        {
            await middleware.InvokeAsync(context, (IAgent)agent, cancellationToken);
        }
    }

    private sealed class ToolCallingAgent(bool replyWithToolCall, bool useUpdates = false) : IStreamingAgent
    {
        public string Name => "agent";

        public Task<IMessage> GenerateReplyAsync(
            IEnumerable<IMessage> messages,
            GenerateReplyOptions? options = null,
            CancellationToken cancellationToken = default)
        {
            IMessage reply = replyWithToolCall
                ? new ToolCallMessage("probe", "{}", Name)
                : new TextMessage(Role.Assistant, "done", Name);
            return Task.FromResult(reply);
        }

        public async IAsyncEnumerable<IMessage> GenerateStreamingReplyAsync(
            IEnumerable<IMessage> messages,
            GenerateReplyOptions? options = null,
            [EnumeratorCancellation] CancellationToken cancellationToken = default)
        {
            if (useUpdates)
            {
                yield return new ToolCallMessageUpdate("probe", "{", Name);
                yield return new ToolCallMessageUpdate("probe", "}", Name);
            }
            else
            {
                yield return await GenerateReplyAsync(messages, options, cancellationToken);
            }
        }
    }
}
