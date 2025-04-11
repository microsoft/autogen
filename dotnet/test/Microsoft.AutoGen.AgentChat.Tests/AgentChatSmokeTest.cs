// Copyright (c) Microsoft Corporation. All rights reserved.
// AgentChatSmokeTest.cs

using System.Text.Json;
using Microsoft.AutoGen.AgentChat.Abstractions;
using Microsoft.AutoGen.AgentChat.Agents;
using Microsoft.AutoGen.AgentChat.GroupChat;
using Microsoft.AutoGen.AgentChat.State;
using Microsoft.AutoGen.AgentChat.Terminations;
using Microsoft.AutoGen.Contracts;
using Xunit;

namespace Microsoft.AutoGen.AgentChat.Tests;

[Trait("Category", "UnitV2")]
public class AgentChatSmokeTest
{
    public class SpeakMessageAgent : ChatAgentBase
    {
        public SpeakMessageAgent(string name, string description, string content) : base(name, description)
        {
            this.Content = content;
        }

        public string Content { get; private set; }

        public override IEnumerable<Type> ProducedMessageTypes => [typeof(HandoffMessage)];

        public override ValueTask<Response> HandleAsync(IEnumerable<ChatMessage> item, CancellationToken cancellationToken)
        {
            Response result = new()
            {
                Message = new TextMessage { Content = this.Content, Source = this.Name }
            };

            return ValueTask.FromResult(result);
        }

        public override ValueTask ResetAsync(CancellationToken cancellationToken)
        {
            return ValueTask.CompletedTask;
        }
    }

    public class TerminatingAgent : ChatAgentBase, ISaveState
    {
        public List<ChatMessage>? IncomingMessages { get; private set; }

        public TerminatingAgent(string name, string description) : base(name, description)
        {
        }

        public override IEnumerable<Type> ProducedMessageTypes => [typeof(StopMessage)];

        public override ValueTask<Response> HandleAsync(IEnumerable<ChatMessage> item, CancellationToken cancellationToken)
        {
            this.IncomingMessages = item.ToList();

            string content = "Terminating";
            if (item.Any())
            {
                ChatMessage lastMessage = item.Last();

                switch (lastMessage)
                {
                    case TextMessage textMessage:
                        content = $"Terminating; got: {textMessage.Content}";
                        break;
                    case HandoffMessage handoffMessage:
                        content = $"Terminating; got handoff: {handoffMessage.Context}";
                        break;
                }
            }

            Response result = new()
            {
                Message = new StopMessage { Content = content, Source = this.Name }
            };

            return ValueTask.FromResult(result);
        }

        public override ValueTask ResetAsync(CancellationToken cancellationToken)
        {
            this.IncomingMessages = null;

            return ValueTask.CompletedTask;
        }

        public class State : BaseState
        {
            public required List<ChatMessage> IncomingMessages { get; set; }
        }

        ValueTask<JsonElement> ISaveState.SaveStateAsync()
        {
            SerializedState serializedState = SerializedState.Create(new State
            {
                IncomingMessages = this.IncomingMessages ?? new List<ChatMessage>()
            });

            return ValueTask.FromResult(serializedState.AsJson());
        }

        ValueTask ISaveState.LoadStateAsync(JsonElement state)
        {
            State parsedState = new SerializedState(state).As<State>();
            this.IncomingMessages = [.. parsedState.IncomingMessages];

            return ValueTask.CompletedTask;
        }
    }

    private ValueTask<TaskResult> RunChatAsync(TerminatingAgent terminatingAgent, out ITeam chat)
    {
        chat = new RoundRobinGroupChat(
            [
                new SpeakMessageAgent("Speak", "Speak", "Hello"),
                terminatingAgent,
            ],
            terminationCondition: new StopMessageTermination());

        return chat.RunAsync("");
    }

    [Fact]
    public async Task Test_RoundRobin_SpeakAndTerminating()
    {
        TerminatingAgent terminatingAgent = new("Terminate", "Terminate");

        TaskResult result = await this.RunChatAsync(terminatingAgent, out _);

        Assert.Equal(3, result.Messages.Count);
        Assert.Equal("", Assert.IsType<TextMessage>(result.Messages[0]).Content);
        Assert.Equal("Hello", Assert.IsType<TextMessage>(result.Messages[1]).Content);
        Assert.Equal("Terminating; got: Hello", Assert.IsType<StopMessage>(result.Messages[2]).Content);
    }

    [Fact]
    public async Task Test_RoundRobin_SpeakTerminateReset()
    {
        TerminatingAgent terminatingAgent = new("Terminate", "Terminate");

        await this.RunChatAsync(terminatingAgent, out ITeam chat);

        Assert.NotNull(terminatingAgent.IncomingMessages);

        await chat.ResetAsync();

        Assert.Null(terminatingAgent.IncomingMessages);
    }

    [Fact]
    public async Task Test_RoundRobin_SaveLoadRun()
    {
        TerminatingAgent t1 = new("Terminate1", "Terminate"), t2 = new("Terminate2", "Terminate");
        SpeakMessageAgent s1 = new("Speak1", "Speak", "Hello"), s2 = new("Speak2", "Speak", "World");

        ITeam chat = new RoundRobinGroupChat(
            [s1, t1, s2, t2],
            terminationCondition: new StopMessageTermination());

        TaskResult result = await chat.RunAsync("1");

        Assert.Equal(3, result.Messages.Count);
        Assert.Equal("1", Assert.IsType<TextMessage>(result.Messages[0]).Content);
        Assert.Equal("Hello", Assert.IsType<TextMessage>(result.Messages[1]).Content);
        Assert.Equal("Terminating; got: Hello", Assert.IsType<StopMessage>(result.Messages[2]).Content);

        // Save state
        JsonElement state = await chat.SaveStateAsync();

        // Reset chat
        await chat.ResetAsync();

        Assert.Null(t1.IncomingMessages);

        // Load state

        await chat.LoadStateAsync(state);

        Assert.NotNull(t1.IncomingMessages);

        // Check that we resume the conversation in the right place
        TaskResult result2 = await chat.RunAsync("2");

        Assert.Equal(3, result.Messages.Count);
        Assert.Equal("2", Assert.IsType<TextMessage>(result2.Messages[0]).Content);
        Assert.Equal("World", Assert.IsType<TextMessage>(result2.Messages[1]).Content);
        Assert.Equal("Terminating; got: World", Assert.IsType<StopMessage>(result2.Messages[2]).Content);

    }
}
