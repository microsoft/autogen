// Copyright (c) Microsoft Corporation. All rights reserved.
// AgentTests.cs
using System.Text.Json;
using FluentAssertions;
using Microsoft.AutoGen.Contracts;
using Microsoft.Extensions.Logging;
using Xunit;

namespace Microsoft.AutoGen.Core.Tests;

[Trait("Category", "UnitV2")]
public class AgentTests()
{
    [Fact]
    public async Task AgentShouldNotReceiveMessagesWhenNotSubscribedTest()
    {
        var runtime = new InProcessRuntime();
        await runtime.StartAsync();

        Logger<BaseAgent> logger = new(new LoggerFactory());
        TestAgent agent = null!;

        await runtime.RegisterAgentFactoryAsync("MyAgent", (id, runtime) =>
        {
            agent = new TestAgent(id, runtime, logger);
            return ValueTask.FromResult(agent);
        });

        // Ensure the agent is actually created
        AgentId agentId = await runtime.GetAgentAsync("MyAgent", lazy: false);

        // Validate agent ID
        agentId.Should().Be(agent.Id, "Agent ID should match the registered agent");

        var topicType = "TestTopic";

        await runtime.PublishMessageAsync(new TextMessage { Source = topicType, Content = "test" }, new TopicId(topicType)).ConfigureAwait(true);
        await runtime.RunUntilIdleAsync();

        agent.ReceivedMessages.Any().Should().BeFalse("Agent should not receive messages when not subscribed.");
    }

    [Fact]
    public async Task AgentShouldReceiveMessagesWhenSubscribedTest()
    {
        var runtime = new InProcessRuntime();
        await runtime.StartAsync();

        Logger<BaseAgent> logger = new(new LoggerFactory());
        SubscribedAgent agent = null!;

        await runtime.RegisterAgentFactoryAsync("MyAgent", (id, runtime) =>
        {
            agent = new SubscribedAgent(id, runtime, logger);
            return ValueTask.FromResult(agent);
        });

        // Ensure the agent id is registered
        AgentId agentId = await runtime.GetAgentAsync("MyAgent", lazy: false);

        // Validate agent ID
        agentId.Should().Be(agent.Id, "Agent ID should match the registered agent");

        await runtime.RegisterImplicitAgentSubscriptionsAsync<SubscribedAgent>("MyAgent");

        var topicType = "TestTopic";

        await runtime.PublishMessageAsync(new TextMessage { Source = topicType, Content = "test" }, new TopicId(topicType)).ConfigureAwait(true);

        await runtime.RunUntilIdleAsync();

        agent.ReceivedMessages.Any().Should().BeTrue("Agent should receive messages when subscribed.");
    }

    [Fact]
    public async Task SendMessageAsyncShouldReturnResponseTest()
    {
        // Arrange
        var runtime = new InProcessRuntime();
        await runtime.StartAsync();

        Logger<BaseAgent> logger = new(new LoggerFactory());
        await runtime.RegisterAgentFactoryAsync("MyAgent", (id, runtime) => ValueTask.FromResult(new TestAgent(id, runtime, logger)));
        await runtime.RegisterImplicitAgentSubscriptionsAsync<TestAgent>("MyAgent");

        var agentId = new AgentId("MyAgent", "TestAgent");

        var response = await runtime.SendMessageAsync(new RpcTextMessage { Source = "TestTopic", Content = "Request" }, agentId);

        // Assert
        Assert.NotNull(response);
        Assert.IsType<string>(response);
        if (response is string responseString)
        {
            Assert.Equal("Request", responseString);
        }
    }

    public class ReceiverAgent(AgentId id,
            IAgentRuntime runtime) : BaseAgent(id, runtime, "Receiver Agent", null),
            IHandle<string>
    {
        public ValueTask HandleAsync(string item, MessageContext messageContext)
        {
            ReceivedItems.Add(item);
            return ValueTask.CompletedTask;
        }

        public List<string> ReceivedItems { get; private set; } = [];
    }

    [Fact]
    public async Task SubscribeAsyncRemoveSubscriptionAsyncTest()
    {
        var runtime = new InProcessRuntime();
        await runtime.StartAsync();
        ReceiverAgent? agent = null;
        await runtime.RegisterAgentFactoryAsync("MyAgent", (id, runtime) =>
        {
            agent = new ReceiverAgent(id, runtime);
            return ValueTask.FromResult(agent);
        });

        Assert.Null(agent);
        await runtime.GetAgentAsync("MyAgent", lazy: false);
        Assert.NotNull(agent);
        Assert.True(agent.ReceivedItems.Count == 0);

        var topicTypeName = "TestTopic";
        await runtime.PublishMessageAsync("info", new TopicId(topicTypeName));
        await Task.Delay(100);

        Assert.True(agent.ReceivedItems.Count == 0);

        var subscription = new TypeSubscription(topicTypeName, "MyAgent");
        await runtime.AddSubscriptionAsync(subscription);

        await runtime.PublishMessageAsync("info", new TopicId(topicTypeName));
        await Task.Delay(100);

        Assert.True(agent.ReceivedItems.Count == 1);
        Assert.Equal("info", agent.ReceivedItems[0]);

        await runtime.RemoveSubscriptionAsync(subscription.Id);
        await runtime.PublishMessageAsync("info", new TopicId(topicTypeName));
        await Task.Delay(100);

        Assert.True(agent.ReceivedItems.Count == 1);
    }

    public class AgentState
    {
        public required string Name { get; set; }
        public required int Value { get; set; }
    }

    public class StateAgent(AgentId id,
        IAgentRuntime runtime,
        AgentState state,
        Logger<BaseAgent>? logger = null) : BaseAgent(id, runtime, "Test Agent", logger),
        ISaveStateMixin<AgentState>

    {
        ValueTask<AgentState> ISaveStateMixin<AgentState>.SaveStateImpl()
        {
            return ValueTask.FromResult(_state);
        }

        ValueTask ISaveStateMixin<AgentState>.LoadStateImpl(AgentState state)
        {
            _state = state;
            return ValueTask.CompletedTask;
        }

        private AgentState _state = state;
    }

    [Fact]
    public async Task StateMixinTest()
    {
        var runtime = new InProcessRuntime();
        await runtime.StartAsync();
        await runtime.RegisterAgentFactoryAsync("MyAgent", (id, runtime) =>
        {
            return ValueTask.FromResult(new StateAgent(id, runtime, new AgentState { Name = "TestAgent", Value = 5 }));
        });

        var agentId = new AgentId("MyAgent", "default");

        // Get the state
        var state1 = await runtime.SaveAgentStateAsync(agentId);

        Assert.Equal("TestAgent", state1.GetProperty("Name").GetString());
        Assert.Equal(5, state1.GetProperty("Value").GetInt32());

        // Change the state
        var newState = new AgentState { Name = "TestAgent", Value = 100 };
        var jsonState = JsonSerializer.SerializeToElement(newState);
        await runtime.LoadAgentStateAsync(agentId, jsonState);

        // Get the state
        var state2 = await runtime.SaveAgentStateAsync(agentId);

        Assert.Equal("TestAgent", state2.GetProperty("Name").GetString());
        Assert.Equal(100, state2.GetProperty("Value").GetInt32());
    }
}
