// Copyright (c) Microsoft Corporation. All rights reserved.
// GroupChatStreamingTests.cs

using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using FluentAssertions;
using Moq;
using Xunit;

namespace AutoGen.Tests;

[Trait("Category", "UnitV1")]
public class GroupChatStreamingTests
{
    [Fact]
    public async Task SubsequentSpeakersReceiveCompleteHistoryAsync()
    {
        var alice = new StreamingProbeAgent("alice", (_, _) => Stream(
            new TextMessageUpdate(Role.Assistant, "hello ", "alice"),
            new TextMessageUpdate(Role.Assistant, "world", "alice")));
        var bob = new RecordingAgent("bob");
        var introduction = new TextMessage(Role.System, "introduction", "bob");
        var task = new TextMessage(Role.User, "task", "bob");
        IStreamingGroupChat group = new GroupChat([alice, bob], initializeMessages: [introduction]);

        var output = await CollectAsync(group.SendStreamingAsync([task], maxRound: 2));

        output.OfType<TextMessageUpdate>().Should().HaveCount(2);
        output.OfType<TextMessage>().Select(message => message.Content).Should().Equal("hello world", "done");
        bob.History.Should().HaveCount(3);
        bob.History[0].Should().BeSameAs(introduction);
        bob.History[1].Should().BeSameAs(task);
        bob.History[2].Should().BeOfType<TextMessage>().Which.Content.Should().Be("hello world");
        bob.History.Should().NotContain(message => message is TextMessageUpdate || message is ToolCallMessageUpdate);
    }

    [Fact]
    public async Task UpdatesAreAvailableBeforeTheAgentFinishesAsync()
    {
        var finish = new TaskCompletionSource<bool>(TaskCreationOptions.RunContinuationsAsynchronously);
        async IAsyncEnumerable<IMessage> Reply()
        {
            yield return new TextMessageUpdate(Role.Assistant, "first", "alice");
            await finish.Task;
            yield return new TextMessageUpdate(Role.Assistant, "second", "alice");
        }

        var alice = new StreamingProbeAgent("alice", (_, _) => Reply());
        var group = new GroupChat([alice]);
        await using var iterator = group.CallStreamingAsync(maxRound: 1).GetAsyncEnumerator();
        try
        {
            (await iterator.MoveNextAsync().AsTask().WaitAsync(TimeSpan.FromSeconds(10))).Should().BeTrue();
            iterator.Current.Should().BeOfType<TextMessageUpdate>().Which.Content.Should().Be("first");
            finish.Task.IsCompleted.Should().BeFalse();
        }
        finally
        {
            finish.TrySetResult(true);
        }

        var remaining = new List<IMessage>();
        while (await iterator.MoveNextAsync())
        {
            remaining.Add(iterator.Current);
        }

        remaining.OfType<TextMessage>().Should().ContainSingle().Which.Content.Should().Be("firstsecond");
    }

    [Fact]
    public async Task CompleteRepliesAreAuthoritativeAsync()
    {
        var complete = new TextMessage(Role.Assistant, "hello", "alice");
        var alice = new StreamingProbeAgent("alice", (_, _) => Stream(
            new TextMessageUpdate(Role.Assistant, "hel", "alice"),
            new TextMessageUpdate(Role.Assistant, "lo", "alice"),
            complete));

        var output = await CollectAsync(new GroupChat([alice]).CallStreamingAsync(maxRound: 1));

        output.Should().HaveCount(3);
        output.OfType<TextMessage>().Should().ContainSingle().Which.Should().BeSameAs(complete);
        complete.Content.Should().Be("hello");
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task ToolCallsArePreservedInHistoryAsync(bool includeCompleteReply)
    {
        var call = new ToolCall("echo", "{\"value\":1}") { ToolCallId = "call-1" };
        var complete = new ToolCallMessage([call], "alice") { Content = "using tool" };
        var chunks = new List<IMessage>
        {
            new TextMessageUpdate(Role.Assistant, "using tool", "alice"),
            new ToolCallMessageUpdate("echo", "{\"value\":", "alice"),
            new ToolCallMessageUpdate("echo", "1}", "alice"),
        };
        if (includeCompleteReply)
        {
            chunks.Add(complete);
        }

        var alice = new StreamingProbeAgent("alice", (_, _) => Stream(chunks.ToArray()));
        var bob = new RecordingAgent("bob");
        var group = new GroupChat([alice, bob]);

        var output = await CollectAsync(group.CallStreamingAsync(maxRound: 2));

        var toolReply = output.OfType<ToolCallMessage>().Should().ContainSingle().Subject;
        toolReply.Content.Should().Be("using tool");
        toolReply.ToolCalls.Should().ContainSingle().Which.FunctionArguments.Should().Be("{\"value\":1}");
        bob.History.Should().ContainSingle().Which.Should().BeSameAs(toolReply);
        if (includeCompleteReply)
        {
            toolReply.Should().BeSameAs(complete);
            toolReply.ToolCalls[0].ToolCallId.Should().Be("call-1");
        }
    }

    [Fact]
    public async Task FunctionCallMiddlewareResultsReachTheNextSpeakerAsync()
    {
        var calls = 0;
        var alice = new StreamingProbeAgent("alice", (_, _) => Stream(
            new ToolCallMessage([new ToolCall("echo", "{}") { ToolCallId = "call-1" }], "alice")));
        var toolAgent = alice.RegisterStreamingMiddleware(new FunctionCallMiddleware(
            functionMap: new Dictionary<string, Func<string, Task<string>>>
            {
                ["echo"] = _ =>
                {
                    calls++;
                    return Task.FromResult("tool result");
                },
            }));
        var bob = new RecordingAgent("bob");
        var group = new GroupChat([toolAgent, bob]);

        var output = await CollectAsync(group.CallStreamingAsync(
            [new TextMessage(Role.User, "use the tool", "bob")], maxRound: 2));

        var aggregate = output.OfType<ToolCallAggregateMessage>().Should().ContainSingle().Subject;
        aggregate.GetContent().Should().Be("tool result");
        aggregate.Message1.ToolCalls[0].ToolCallId.Should().Be("call-1");
        aggregate.Message2.ToolCalls[0].ToolCallId.Should().Be("call-1");
        bob.History[^1].Should().BeSameAs(aggregate);
        calls.Should().Be(1);
    }

    [Theory]
    [InlineData(-1, 0)]
    [InlineData(0, 0)]
    [InlineData(2, 2)]
    public async Task TurnLimitsAreRespectedAsync(int maxRound, int expectedCalls)
    {
        var alice = new StreamingProbeAgent("alice", (_, _) => Stream(new TextMessage(Role.Assistant, "hello", "alice")));
        var group = new RoundRobinGroupChat([alice]);

        var output = await CollectAsync(group.SendStreamingAsync(maxRound: maxRound));

        output.Should().HaveCount(expectedCalls);
        alice.StreamingCalls.Should().Be(expectedCalls);
    }

    [Fact]
    public async Task TerminationIsCheckedOnTheMergedReplyAsync()
    {
        var alice = new StreamingProbeAgent("alice", (_, _) => Stream(
            new TextMessageUpdate(Role.Assistant, "[GROUPCHAT_", "alice"),
            new TextMessageUpdate(Role.Assistant, "TERMINATE]", "alice")));
        var bob = new RecordingAgent("bob");

        var output = await CollectAsync(new GroupChat([alice, bob]).CallStreamingAsync());

        output.OfType<TextMessage>().Should().ContainSingle().Which.Content.Should().Be(GroupChatExtension.TERMINATE);
        alice.StreamingCalls.Should().Be(1);
        bob.Calls.Should().Be(0);
    }

    [Fact]
    public async Task NoSpeakerEndsTheStreamAsync()
    {
        var output = await CollectAsync(new GroupChat([]).CallStreamingAsync());

        output.Should().BeEmpty();
    }

    [Fact]
    public async Task EmptyAgentStreamsFailExplicitlyAsync()
    {
        var alice = new StreamingProbeAgent("alice", (_, _) => Stream());
        var group = new GroupChat([alice]);

        Func<Task> run = () => CollectAsync(group.CallStreamingAsync(maxRound: 1));

        await run.Should().ThrowAsync<InvalidOperationException>().WithMessage("*alice*without a reply*");
    }

    [Fact]
    public async Task EnumeratorCancellationPreventsAgentInvocationAsync()
    {
        using var cancellation = new CancellationTokenSource();
        cancellation.Cancel();
        var alice = new StreamingProbeAgent("alice", (_, _) => Stream(new TextMessage(Role.Assistant, "hello", "alice")));
        var group = new GroupChat([alice]);
        Func<Task> run = async () =>
        {
            await foreach (var _ in group.CallStreamingAsync().WithCancellation(cancellation.Token))
            {
            }
        };

        await run.Should().ThrowAsync<OperationCanceledException>();

        alice.StreamingCalls.Should().Be(0);
    }

    [Fact]
    public async Task CancellationStopsUpdatesAndDisposesTheAgentStreamAsync()
    {
        using var cancellation = new CancellationTokenSource();
        var disposed = false;
        async IAsyncEnumerable<IMessage> Reply()
        {
            try
            {
                await Task.Yield();
                yield return new TextMessageUpdate(Role.Assistant, "first", "alice");
                cancellation.Cancel();
                yield return new TextMessageUpdate(Role.Assistant, "not delivered", "alice");
            }
            finally
            {
                disposed = true;
            }
        }

        var alice = new StreamingProbeAgent("alice", (_, _) => Reply());
        var bob = new RecordingAgent("bob");
        var group = new GroupChat([alice, bob]);
        var output = new List<IMessage>();
        Func<Task> run = async () =>
        {
            await foreach (var message in group.SendStreamingAsync(cancellationToken: cancellation.Token))
            {
                output.Add(message);
            }
        };

        await run.Should().ThrowAsync<OperationCanceledException>();

        output.Should().ContainSingle().Which.Should().BeOfType<TextMessageUpdate>().Which.Content.Should().Be("first");
        alice.ObservedToken.Should().Be(cancellation.Token);
        bob.Calls.Should().Be(0);
        disposed.Should().BeTrue();
    }

    [Fact]
    public async Task DisposingTheGroupStreamDisposesTheAgentStreamAsync()
    {
        var disposed = false;
        async IAsyncEnumerable<IMessage> Reply()
        {
            try
            {
                await Task.Yield();
                yield return new TextMessageUpdate(Role.Assistant, "first", "alice");
                yield return new TextMessageUpdate(Role.Assistant, "second", "alice");
            }
            finally
            {
                disposed = true;
            }
        }

        var alice = new StreamingProbeAgent("alice", (_, _) => Reply());
        var iterator = new GroupChat([alice]).CallStreamingAsync(maxRound: 1).GetAsyncEnumerator();
        (await iterator.MoveNextAsync()).Should().BeTrue();

        await iterator.DisposeAsync();

        disposed.Should().BeTrue();
    }

    [Fact]
    public async Task CancellationIsForwardedToTheOrchestratorAndNonStreamingMembersAsync()
    {
        using var cancellation = new CancellationTokenSource();
        var bob = new RecordingAgent("bob");
        var orchestrator = new Mock<IOrchestrator>();
        orchestrator.Setup(value => value.GetNextSpeakerAsync(
            It.IsAny<OrchestrationContext>(), cancellation.Token)).ReturnsAsync(bob);
        var group = new GroupChat([bob], orchestrator.Object);

        var output = await CollectAsync(group.SendStreamingAsync(maxRound: 1, cancellationToken: cancellation.Token));

        output.Should().ContainSingle().Which.GetContent().Should().Be("done");
        bob.ObservedToken.Should().Be(cancellation.Token);
        orchestrator.Verify(value => value.GetNextSpeakerAsync(
            It.IsAny<OrchestrationContext>(), cancellation.Token), Times.Once);
    }

    [Fact]
    public async Task AgentFailuresArePropagatedAndDisposeTheStreamAsync()
    {
        var disposed = false;
        async IAsyncEnumerable<IMessage> Reply()
        {
            try
            {
                await Task.Yield();
                yield return new TextMessageUpdate(Role.Assistant, "first", "alice");
                throw new InvalidOperationException("generation failed");
            }
            finally
            {
                disposed = true;
            }
        }

        var alice = new StreamingProbeAgent("alice", (_, _) => Reply());
        var bob = new RecordingAgent("bob");
        var group = new GroupChat([alice, bob]);
        Func<Task> run = () => CollectAsync(group.CallStreamingAsync());

        await run.Should().ThrowAsync<InvalidOperationException>().WithMessage("generation failed");

        disposed.Should().BeTrue();
        bob.Calls.Should().Be(0);
    }

    private static async Task<List<IMessage>> CollectAsync(IAsyncEnumerable<IMessage> messages)
    {
        var output = new List<IMessage>();
        await foreach (var message in messages)
        {
            output.Add(message);
        }

        return output;
    }

    private static async IAsyncEnumerable<IMessage> Stream(params IMessage[] messages)
    {
        foreach (var message in messages)
        {
            await Task.Yield();
            yield return message;
        }
    }

    private sealed class StreamingProbeAgent(
        string name,
        Func<IReadOnlyList<IMessage>, CancellationToken, IAsyncEnumerable<IMessage>> reply) : IStreamingAgent
    {
        public string Name => name;

        public int StreamingCalls { get; private set; }

        public CancellationToken ObservedToken { get; private set; }

        public Task<IMessage> GenerateReplyAsync(
            IEnumerable<IMessage> messages,
            GenerateReplyOptions? options = null,
            CancellationToken cancellationToken = default)
        {
            throw new InvalidOperationException("The streaming path should be used.");
        }

        public IAsyncEnumerable<IMessage> GenerateStreamingReplyAsync(
            IEnumerable<IMessage> messages,
            GenerateReplyOptions? options = null,
            CancellationToken cancellationToken = default)
        {
            StreamingCalls++;
            ObservedToken = cancellationToken;
            return reply(messages.ToArray(), cancellationToken);
        }
    }

    private sealed class RecordingAgent(string name) : IAgent
    {
        public string Name => name;

        public IReadOnlyList<IMessage> History { get; private set; } = [];

        public int Calls { get; private set; }

        public CancellationToken ObservedToken { get; private set; }

        public Task<IMessage> GenerateReplyAsync(
            IEnumerable<IMessage> messages,
            GenerateReplyOptions? options = null,
            CancellationToken cancellationToken = default)
        {
            cancellationToken.ThrowIfCancellationRequested();
            History = messages.ToArray();
            ObservedToken = cancellationToken;
            Calls++;
            return Task.FromResult<IMessage>(new TextMessage(Role.Assistant, "done", Name));
        }
    }
}
