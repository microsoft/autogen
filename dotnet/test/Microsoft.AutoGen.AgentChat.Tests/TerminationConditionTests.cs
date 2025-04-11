// Copyright (c) Microsoft Corporation. All rights reserved.
// TerminationConditionTests.cs

using FluentAssertions;
using Microsoft.AutoGen.AgentChat.Abstractions;
using Microsoft.AutoGen.AgentChat.Terminations;
using Microsoft.Extensions.AI;
using Xunit;

namespace Microsoft.AutoGen.AgentChat.Tests;

[Trait("Category", "UnitV2")]
public static class TerminationExtensions
{
    public static async Task InvokeExpectingNullAsync<TTermination>(this TTermination termination, IList<AgentMessage> messages, bool reset = true)
        where TTermination : ITerminationCondition
    {
        (await termination.CheckAndUpdateAsync(messages)).Should().BeNull();
        termination.IsTerminated.Should().BeFalse();

        if (reset)
        {
            termination.Reset();
        }
    }

    private static readonly HashSet<string> AnonymousTerminationConditions = ["CombinerCondition", nameof(ITerminationCondition)];
    public static async Task InvokeExpectingStopAsync<TTermination>(this TTermination termination, IList<AgentMessage> messages, bool reset = true)
        where TTermination : ITerminationCondition
    {
        StopMessage? stopMessage = await termination.CheckAndUpdateAsync(messages);
        stopMessage.Should().NotBeNull();

        string name = typeof(TTermination).Name;
        if (!AnonymousTerminationConditions.Contains(name))
        {
            stopMessage!.Source.Should().Be(typeof(TTermination).Name);
        }

        termination.IsTerminated.Should().BeTrue();

        if (reset)
        {
            termination.Reset();
        }
    }

    public static async Task InvokeExpectingFailureAsync<TTermination>(this TTermination termination, IList<AgentMessage> messages, bool reset = true)
        where TTermination : ITerminationCondition
    {
        Func<Task> failureAction = () => termination.CheckAndUpdateAsync(messages).AsTask();
        await failureAction.Should().ThrowAsync<TerminatedException>();
        termination.IsTerminated.Should().BeTrue();

        if (reset)
        {
            termination.Reset();
        }
    }
}

public class TerminationConditionTests
{
    [Fact]
    public async Task Test_HandoffTermination()
    {
        HandoffTermination termination = new("target");
        termination.IsTerminated.Should().BeFalse();

        TextMessage textMessage = new() { Content = "Hello", Source = "user" };
        HandoffMessage targetHandoffMessage = new() { Target = "target", Source = "user", Context = "Hello" };
        HandoffMessage otherHandoffMessage = new() { Target = "another", Source = "user", Context = "Hello" };

        await termination.InvokeExpectingNullAsync([]);
        await termination.InvokeExpectingNullAsync([textMessage]);
        await termination.InvokeExpectingStopAsync([targetHandoffMessage]);
        await termination.InvokeExpectingNullAsync([otherHandoffMessage]);
        await termination.InvokeExpectingStopAsync([textMessage, targetHandoffMessage], reset: false);

        await termination.InvokeExpectingFailureAsync([], reset: false);

        termination.Reset();
        termination.IsTerminated.Should().BeFalse();
    }

    [Fact]
    public async Task StopMessageTermination()
    {
        StopMessageTermination termination = new();
        termination.IsTerminated.Should().BeFalse();

        TextMessage textMessage = new() { Content = "Hello", Source = "user" };
        TextMessage otherMessage = new() { Content = "World", Source = "aser" };
        StopMessage stopMessage = new() { Content = "Stop", Source = "user" };

        await termination.InvokeExpectingNullAsync([]);
        await termination.InvokeExpectingNullAsync([textMessage]);
        await termination.InvokeExpectingStopAsync([stopMessage]);
        await termination.InvokeExpectingNullAsync([textMessage, otherMessage]);
        await termination.InvokeExpectingStopAsync([textMessage, stopMessage], reset: false);

        await termination.InvokeExpectingFailureAsync([], reset: false);

        termination.Reset();
        termination.IsTerminated.Should().BeFalse();
    }

    [Fact]
    public async Task Test_TextMesssageTermination()
    {
        TextMessageTermination termination = new();
        termination.IsTerminated.Should().BeFalse();

        TextMessage userMessage = new() { Content = "Hello", Source = "user" };
        TextMessage agentMessage = new() { Content = "World", Source = "agent" };
        StopMessage stopMessage = new() { Content = "Stop", Source = "user" };

        await termination.InvokeExpectingNullAsync([]);
        await termination.InvokeExpectingStopAsync([userMessage]);
        await termination.InvokeExpectingStopAsync([agentMessage]);
        await termination.InvokeExpectingNullAsync([stopMessage]);

        termination = new("user");

        await termination.InvokeExpectingNullAsync([agentMessage]);
        await termination.InvokeExpectingNullAsync([stopMessage]);
        await termination.InvokeExpectingStopAsync([userMessage], reset: false);

        await termination.InvokeExpectingFailureAsync([], reset: false);

        termination.Reset();
        termination.IsTerminated.Should().BeFalse();
    }

    [Fact]
    public async Task MaxMessageTermination()
    {
        MaxMessageTermination termination = new(2);
        termination.IsTerminated.Should().BeFalse();

        TextMessage textMessage = new() { Content = "Hello", Source = "user" };
        TextMessage otherMessage = new() { Content = "World", Source = "agent" };
        UserInputRequestedEvent uiRequest = new() { Source = "agent", RequestId = "1" };

        await termination.InvokeExpectingNullAsync([]);
        await termination.InvokeExpectingNullAsync([textMessage]);
        await termination.InvokeExpectingStopAsync([textMessage, otherMessage]);
        await termination.InvokeExpectingNullAsync([textMessage, uiRequest]);

        termination = new(2, includeAgentEvent: true);

        await termination.InvokeExpectingStopAsync([textMessage, uiRequest], reset: false);

        await termination.InvokeExpectingFailureAsync([], reset: false);

        termination.Reset();
        termination.IsTerminated.Should().BeFalse();
    }

    [Fact]
    public async Task Test_TextMentionTermination()
    {
        TextMentionTermination termination = new("stop");
        termination.IsTerminated.Should().BeFalse();

        TextMessage textMessage = new() { Content = "Hello", Source = "user" };
        TextMessage userStopMessage = new() { Content = "stop", Source = "user" };
        TextMessage agentStopMessage = new() { Content = "stop", Source = "agent" };

        await termination.InvokeExpectingNullAsync([]);
        await termination.InvokeExpectingNullAsync([textMessage]);
        await termination.InvokeExpectingStopAsync([userStopMessage]);

        termination = new("stop", sources: ["agent"]);

        await termination.InvokeExpectingNullAsync([textMessage]);
        await termination.InvokeExpectingNullAsync([userStopMessage]);
        await termination.InvokeExpectingStopAsync([agentStopMessage], reset: false);

        await termination.InvokeExpectingFailureAsync([], reset: false);

        termination.Reset();
        termination.IsTerminated.Should().BeFalse();
    }

    [Fact]
    public async Task Text_TokenUsageTermination()
    {
        TokenUsageTermination termination = new(10);
        termination.IsTerminated.Should().BeFalse();

        RequestUsage usage_10_10 = new() { CompletionTokens = 10, PromptTokens = 10 };
        RequestUsage usage_01_01 = new() { CompletionTokens = 1, PromptTokens = 1 };
        RequestUsage usage_05_00 = new() { CompletionTokens = 5, PromptTokens = 0 };
        RequestUsage usage_00_05 = new() { CompletionTokens = 0, PromptTokens = 5 };

        await termination.InvokeExpectingNullAsync([]);

        await termination.InvokeExpectingStopAsync([
            new TextMessage { Content = "Hello", Source = "user", ModelUsage = usage_10_10 },
        ]);

        await termination.InvokeExpectingNullAsync([
            new TextMessage { Content = "Hello", Source = "user", ModelUsage = usage_01_01 },
            new TextMessage { Content = "World", Source = "agent", ModelUsage = usage_01_01 },
        ]);

        await termination.InvokeExpectingStopAsync([
            new TextMessage { Content = "Hello", Source = "user", ModelUsage = usage_05_00 },
            new TextMessage { Content = "World", Source = "agent", ModelUsage = usage_00_05 },
        ], reset: false);

        await termination.InvokeExpectingFailureAsync([], reset: false);

        termination.Reset();
        termination.IsTerminated.Should().BeFalse();
    }

    public class AgentTextEvent : AgentEvent
    {
        public required string Content { get; set; }

        public override Extensions.AI.ChatMessage ToCompletionClientMessage(ChatRole role)
        {
            return new Extensions.AI.ChatMessage(ChatRole.Assistant, this.Content);
        }
    }

    [Fact]
    public async Task Text_Termination_AndCombinator()
    {
        ITerminationCondition lhsClause = new MaxMessageTermination(2);
        ITerminationCondition rhsClause = new TextMentionTermination("stop");

        ITerminationCondition termination = lhsClause & rhsClause;
        termination.IsTerminated.Should().BeFalse();

        TextMessage userMessage = new() { Content = "Hello", Source = "user" };
        AgentTextEvent agentMessage = new() { Content = "World", Source = "agent" };

        TextMessage userStopMessage = new() { Content = "stop", Source = "user" };

        await termination.InvokeExpectingNullAsync([]);

        await termination.InvokeExpectingNullAsync([userMessage]);

        await termination.InvokeExpectingNullAsync([userMessage, agentMessage], reset: false);
        lhsClause.IsTerminated.Should().BeFalse();
        rhsClause.IsTerminated.Should().BeFalse();

        await termination.InvokeExpectingStopAsync([userStopMessage], reset: false);

        lhsClause.IsTerminated.Should().BeTrue();
        rhsClause.IsTerminated.Should().BeTrue();
        termination.IsTerminated.Should().BeTrue();

        await termination.InvokeExpectingFailureAsync([], reset: false);

        lhsClause.IsTerminated.Should().BeTrue();
        rhsClause.IsTerminated.Should().BeTrue();
        termination.IsTerminated.Should().BeTrue();

        termination.Reset();
        termination.IsTerminated.Should().BeFalse();

        await termination.InvokeExpectingNullAsync([userMessage, agentMessage], reset: false);
        lhsClause.IsTerminated.Should().BeFalse();
        rhsClause.IsTerminated.Should().BeFalse();

        await termination.InvokeExpectingNullAsync([userMessage], reset: false);

        lhsClause.IsTerminated.Should().BeTrue();
        rhsClause.IsTerminated.Should().BeFalse();
        termination.IsTerminated.Should().BeFalse();

        await termination.InvokeExpectingNullAsync([userMessage], reset: false);

        lhsClause.IsTerminated.Should().BeTrue();
        rhsClause.IsTerminated.Should().BeFalse();
        termination.IsTerminated.Should().BeFalse();

        await termination.InvokeExpectingStopAsync([userStopMessage], reset: false);

        lhsClause.IsTerminated.Should().BeTrue();
        rhsClause.IsTerminated.Should().BeTrue();
        termination.IsTerminated.Should().BeTrue();

        await termination.InvokeExpectingFailureAsync([], reset: false);

        lhsClause.IsTerminated.Should().BeTrue();
        rhsClause.IsTerminated.Should().BeTrue();
        termination.IsTerminated.Should().BeTrue();

        termination.Reset();
        termination.IsTerminated.Should().BeFalse();

        await termination.InvokeExpectingNullAsync([agentMessage, userStopMessage], reset: false);

        lhsClause.IsTerminated.Should().BeFalse();
        rhsClause.IsTerminated.Should().BeTrue();
        termination.IsTerminated.Should().BeFalse();

        await termination.InvokeExpectingStopAsync([userMessage], reset: false);
        lhsClause.IsTerminated.Should().BeTrue();
        rhsClause.IsTerminated.Should().BeTrue();
        termination.IsTerminated.Should().BeTrue();

        await termination.InvokeExpectingFailureAsync([], reset: false);
        lhsClause.IsTerminated.Should().BeTrue();
        rhsClause.IsTerminated.Should().BeTrue();
        termination.IsTerminated.Should().BeTrue();

        termination.Reset();
        termination.IsTerminated.Should().BeFalse();
    }

    [Fact]
    public async Task Test_Termination_OrCombiner()
    {
        ITerminationCondition lhsClause = new MaxMessageTermination(3);
        ITerminationCondition rhsClause = new TextMentionTermination("stop");

        ITerminationCondition termination = lhsClause | rhsClause;
        termination.IsTerminated.Should().BeFalse();

        TextMessage userMessage = new() { Content = "Hello", Source = "user" };
        AgentTextEvent agentMessage = new() { Content = "World", Source = "agent" };
        TextMessage userStopMessage = new() { Content = "stop", Source = "user" };

        await termination.InvokeExpectingNullAsync([]);
        await termination.InvokeExpectingNullAsync([userMessage]);
        await termination.InvokeExpectingNullAsync([userMessage, agentMessage]);

        await termination.InvokeExpectingNullAsync([userMessage, agentMessage, userMessage], reset: false);
        lhsClause.IsTerminated.Should().BeFalse();
        rhsClause.IsTerminated.Should().BeFalse();
        termination.IsTerminated.Should().BeFalse();

        termination.Reset();
        termination.IsTerminated.Should().BeFalse();

        await termination.InvokeExpectingStopAsync([userMessage, agentMessage, userStopMessage], reset: false);
        lhsClause.IsTerminated.Should().BeFalse();
        rhsClause.IsTerminated.Should().BeTrue();
        termination.IsTerminated.Should().BeTrue();

        await termination.InvokeExpectingFailureAsync([], reset: false);
        lhsClause.IsTerminated.Should().BeFalse();
        rhsClause.IsTerminated.Should().BeTrue();
        termination.IsTerminated.Should().BeTrue();

        termination.Reset();
        termination.IsTerminated.Should().BeFalse();

        await termination.InvokeExpectingStopAsync([userMessage, userMessage, userMessage], reset: false);
        lhsClause.IsTerminated.Should().BeTrue();
        rhsClause.IsTerminated.Should().BeFalse();
        termination.IsTerminated.Should().BeTrue();

        await termination.InvokeExpectingFailureAsync([], reset: false);
        lhsClause.IsTerminated.Should().BeTrue();
        rhsClause.IsTerminated.Should().BeFalse();
        termination.IsTerminated.Should().BeTrue();

        termination.Reset();
        termination.IsTerminated.Should().BeFalse();
    }

    [Fact]
    public async Task Test_TimeoutTermination()
    {
        TextMessage userMessage = new() { Content = "Hello", Source = "user" };

        TimeoutTermination termination = new(0.15f);
        termination.IsTerminated.Should().BeFalse();

        await termination.InvokeExpectingNullAsync([]);

        await Task.Delay(TimeSpan.FromSeconds(0.20f));

        await termination.InvokeExpectingStopAsync([], reset: false);

        await termination.InvokeExpectingFailureAsync([], reset: false);

        termination.Reset();
        termination.IsTerminated.Should().BeFalse();

        await termination.InvokeExpectingNullAsync([userMessage]);

        await Task.Delay(TimeSpan.FromSeconds(0.20f));

        await termination.InvokeExpectingStopAsync([], reset: false);
    }

    [Fact]
    public async Task Test_ExternalTermination()
    {
        ExternalTermination termination = new();
        termination.IsTerminated.Should().BeFalse();

        TextMessage userMessage = new() { Content = "Hello", Source = "user" };

        await termination.InvokeExpectingNullAsync([]);
        await termination.InvokeExpectingNullAsync([userMessage]);

        termination.Set();
        termination.IsTerminated.Should().BeFalse(); // We only terminate on the next check

        await termination.InvokeExpectingStopAsync([], reset: false);
        await termination.InvokeExpectingFailureAsync([], reset: false);

        termination.Reset();
        termination.IsTerminated.Should().BeFalse();

        await termination.InvokeExpectingNullAsync([userMessage]);
    }

    private ToolCallRequestEvent CreateFunctionRequest(string functionName, string id = "1", string arguments = "")
    {
        ToolCallRequestEvent result = new ToolCallRequestEvent
        {
            Source = "agent"
        };

        result.Content.Add(
            new FunctionCall
            {
                Id = id,
                Name = functionName,
                Arguments = arguments,
            });

        return result;
    }

    private ToolCallExecutionEvent CreateFunctionResponse(string functionName, string id = "1", string content = "")
    {
        ToolCallExecutionEvent result = new ToolCallExecutionEvent
        {
            Source = "agent"
        };

        result.Content.Add(
            new FunctionExecutionResult
            {
                Id = id,
                Name = functionName,
                Content = content,
            });

        return result;
    }

    [Fact]
    public async Task Test_FunctionCallTermination()
    {
        FunctionCallTermination termination = new("test_function");
        termination.IsTerminated.Should().BeFalse();

        TextMessage userMessage = new() { Content = "Hello", Source = "user" };
        ToolCallRequestEvent toolCallRequest = CreateFunctionRequest("test_function");
        ToolCallExecutionEvent testExecution = CreateFunctionResponse("test_function");
        ToolCallExecutionEvent otherExecution = CreateFunctionResponse("other_function");

        await termination.InvokeExpectingNullAsync([]);
        await termination.InvokeExpectingNullAsync([userMessage]);
        await termination.InvokeExpectingNullAsync([toolCallRequest]);
        await termination.InvokeExpectingNullAsync([otherExecution]);
        await termination.InvokeExpectingStopAsync([testExecution], reset: false);

        await termination.InvokeExpectingFailureAsync([], reset: false);

        termination.Reset();
        termination.IsTerminated.Should().BeFalse();
    }
}
