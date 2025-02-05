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

    [Fact]
    public async Task AgentShouldSaveLoadStateCorrectlyTest()
    {
        var runtime = new InProcessRuntime();
        await runtime.StartAsync();

        Logger<BaseAgent> logger = new(new LoggerFactory());
        SubscribedSaveLoadAgent agent = null!;

        await runtime.RegisterAgentFactoryAsync("MyAgent", (id, runtime) =>
        {
            agent = new SubscribedSaveLoadAgent(id, runtime, logger);
            return ValueTask.FromResult(agent);
        });

        // Ensure the agent id is registered
        AgentId agentId = await runtime.GetAgentAsync("MyAgent", lazy: false);

        // Validate agent ID
        agentId.Should().Be(agent.Id, "Agent ID should match the registered agent");

        await runtime.RegisterImplicitAgentSubscriptionsAsync<SubscribedSaveLoadAgent>("MyAgent");

        var topicType = "TestTopic";

        await runtime.PublishMessageAsync(new TextMessage { Source = topicType, Content = "test" }, new TopicId(topicType)).ConfigureAwait(true);

        await runtime.RunUntilIdleAsync();

        agent.ReceivedMessages.Any().Should().BeTrue("Agent should receive messages when subscribed.");

        // Save the state
        var savedState = await agent.SaveStateAsync();

        // Ensure the state contains receivedMessages
        savedState.Should().ContainKey("TestTopic");

        // Ensure the value is a valid JsonElement
        savedState["TestTopic"].ValueKind.Should().Be(JsonValueKind.String, "Expected 'TestTopic' to be a string");

        // Verify JSON serialization
        string json = JsonSerializer.Serialize(savedState);
        json.Should().NotBeNullOrEmpty("Serialized state should not be empty");

        // Deserialize and ensure correctness
        var deserializedState = JsonSerializer.Deserialize<Dictionary<string, JsonElement>>(json)
            ?? throw new Exception("Deserialized state is unexpectedly null");

        deserializedState.Should().ContainKey("TestTopic");
        deserializedState["TestTopic"].ValueKind.Should().Be(JsonValueKind.String, "Expected 'TestTopic' to be a string");

        // Get the string value safely
        string testValue = deserializedState["TestTopic"].GetString()
            ?? throw new Exception("Value should not be null");
        testValue.Should().Be("test");

        // Create a new instance of the agent to simulate a restart
        var newAgent = new SubscribedSaveLoadAgent(agent.Id, runtime, logger);

        // Load the saved state into the new agent
        await newAgent.LoadStateAsync(savedState);

        // Verify that the loaded state contains the received message
        newAgent.ReceivedMessages.Should().ContainKey(topicType);
        ((JsonElement)newAgent.ReceivedMessages[topicType]).GetString().Should().Be("test");
    }
}
