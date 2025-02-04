// Copyright (c) Microsoft Corporation. All rights reserved.
// AgentGrpcTests.cs
using FluentAssertions;
using Microsoft.AutoGen.Contracts;
using Microsoft.Extensions.Logging;
using Microsoft.AutoGen.Core.Tests;

using Xunit;

namespace Microsoft.AutoGen.Core.Grpc.Tests;

[Trait("Category", "UnitV2")]
public class AgentGrpcTests
{
    [Fact]
    public async Task AgentShouldNotReceiveMessagesWhenNotSubscribedTest()
    {
        var fixture = new GrpcAgentRuntimeFixture();
        var runtime = (GrpcAgentRuntime)await fixture.Start();

        Logger<BaseAgent> logger = new(new LoggerFactory());
        TestAgent agent = null!;

        await runtime.RegisterAgentFactoryAsync("MyAgent", async (id, runtime) =>
        {
            agent = new TestAgent(id, runtime, logger);
            return await ValueTask.FromResult(agent);
        });

        // Ensure the agent is actually created
        AgentId agentId = await runtime.GetAgentAsync("MyAgent", lazy: false);

        // Validate agent ID
        agentId.Should().Be(agent.Id, "Agent ID should match the registered agent");

        var topicType = "TestTopic";

        await runtime.PublishMessageAsync(new Core.Tests.TextMessage { Source = topicType, Content = "test" }, new TopicId(topicType)).ConfigureAwait(true);

        agent.ReceivedMessages.Any().Should().BeFalse("Agent should not receive messages when not subscribed.");
        fixture.Dispose();
    }

    [Fact]
    public async Task AgentShouldReceiveMessagesWhenSubscribedTest()
    {
        var fixture = new GrpcAgentRuntimeFixture();
        var runtime = (GrpcAgentRuntime)await fixture.Start();

        Logger<BaseAgent> logger = new(new LoggerFactory());
        SubscribedAgent agent = null!;

        await runtime.RegisterAgentFactoryAsync("MyAgent", async (id, runtime) =>
        {
            agent = new SubscribedAgent(id, runtime, logger);
            return await ValueTask.FromResult(agent);
        });

        // Ensure the agent is actually created
        AgentId agentId = await runtime.GetAgentAsync("MyAgent", lazy: false);

        // Validate agent ID
        agentId.Should().Be(agent.Id, "Agent ID should match the registered agent");

        await runtime.RegisterImplicitAgentSubscriptionsAsync<SubscribedAgent>("MyAgent");

        var topicType = "TestTopic";

        await runtime.PublishMessageAsync(new Core.Tests.TextMessage { Source = topicType, Content = "test" }, new TopicId(topicType)).ConfigureAwait(true);

        agent.ReceivedMessages.Any().Should().BeTrue("Agent should receive messages when subscribed.");
    }

    [Fact]
    public async Task SendMessageAsyncShouldReturnResponseTest()
    {
        // Arrange
        var fixture = new GrpcAgentRuntimeFixture();
        var runtime = (GrpcAgentRuntime)await fixture.Start();

        Logger<BaseAgent> logger = new(new LoggerFactory());
        await runtime.RegisterAgentFactoryAsync("MyAgent", async (id, runtime) => await ValueTask.FromResult(new TestAgent(id, runtime, logger)));
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
    public async Task SubscribeAsyncRemoveSubscriptionAsyncAndGetSubscriptionsTest()
    {
        var fixture = new GrpcAgentRuntimeFixture();
        var runtime = (GrpcAgentRuntime)await fixture.Start();
        ReceiverAgent? agent = null;
        await runtime.RegisterAgentFactoryAsync("MyAgent", async (id, runtime) =>
        {
            agent = new ReceiverAgent(id, runtime);
            return await ValueTask.FromResult(agent);
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
    public async Task AgentShouldSaveStateCorrectlyTest()
    {

        var fixture = new GrpcAgentRuntimeFixture();
        var runtime = (GrpcAgentRuntime)await fixture.Start();

        Logger<BaseAgent> logger = new(new LoggerFactory());
        TestAgent agent = new TestAgent(new AgentId("TestType", "TestKey"), runtime, logger);

        var state = await agent.SaveStateAsync();

        // Ensure state is a dictionary
        state.Should().NotBeNull();
        state.Should().BeOfType<Dictionary<string, object>>();
        state.Should().BeEmpty("Default SaveStateAsync should return an empty dictionary.");

        // Add a sample value and verify it updates correctly
        state["testKey"] = "testValue";
        state.Should().ContainKey("testKey").WhoseValue.Should().Be("testValue");
    }
}
