// Copyright (c) Microsoft Corporation. All rights reserved.
// AgentGrpcTests.cs
using FluentAssertions;
using Microsoft.AutoGen.Contracts;
// using Microsoft.AutoGen.Core.Tests;
using Microsoft.AutoGen.Core.Grpc.Tests.Protobuf;
using Microsoft.Extensions.Logging;
using Xunit;

namespace Microsoft.AutoGen.Core.Grpc.Tests;

[Trait("Category", "GRPC")]
public class AgentGrpcTests
{
    [Fact]
    public async Task AgentShouldNotReceiveMessagesWhenNotSubscribedTest()
    {
        var fixture = new GrpcAgentRuntimeFixture();
        var runtime = (GrpcAgentRuntime)await fixture.Start();

        Logger<BaseAgent> logger = new(new LoggerFactory());
        TestProtobufAgent agent = null!;

        await runtime.RegisterAgentFactoryAsync("MyAgent", async (id, runtime) =>
        {
            agent = new TestProtobufAgent(id, runtime, logger);
            return await ValueTask.FromResult(agent);
        });

        // Ensure the agent is actually created
        AgentId agentId = await runtime.GetAgentAsync("MyAgent", lazy: false);

        // Validate agent ID
        agentId.Should().Be(agent.Id, "Agent ID should match the registered agent");

        var topicType = "TestTopic";

        await runtime.PublishMessageAsync(new Protobuf.TextMessage { Source = topicType, Content = "test" }, new TopicId(topicType)).ConfigureAwait(true);

        agent.ReceivedMessages.Any().Should().BeFalse("Agent should not receive messages when not subscribed.");
        fixture.Dispose();
    }

    [Fact]
    public async Task AgentShouldReceiveMessagesWhenSubscribedTest()
    {
        var fixture = new GrpcAgentRuntimeFixture();
        var runtime = (GrpcAgentRuntime)await fixture.Start();

        Logger<BaseAgent> logger = new(new LoggerFactory());
        SubscribedProtobufAgent agent = null!;

        await runtime.RegisterAgentFactoryAsync("MyAgent", async (id, runtime) =>
        {
            agent = new SubscribedProtobufAgent(id, runtime, logger);
            return await ValueTask.FromResult(agent);
        });

        // Ensure the agent is actually created
        AgentId agentId = await runtime.GetAgentAsync("MyAgent", lazy: false);

        // Validate agent ID
        agentId.Should().Be(agent.Id, "Agent ID should match the registered agent");

        await runtime.RegisterImplicitAgentSubscriptionsAsync<SubscribedProtobufAgent>("MyAgent");

        var topicType = "TestTopic";

        await runtime.PublishMessageAsync(new TextMessage { Source = topicType, Content = "test" }, new TopicId(topicType)).ConfigureAwait(true);

        // Wait for the message to be processed
        await Task.Delay(100);

        agent.ReceivedMessages.Any().Should().BeTrue("Agent should receive messages when subscribed.");
        fixture.Dispose();
    }

    [Fact]
    public async Task SendMessageAsyncShouldReturnResponseTest()
    {
        // Arrange
        var fixture = new GrpcAgentRuntimeFixture();
        var runtime = (GrpcAgentRuntime)await fixture.Start();

        Logger<BaseAgent> logger = new(new LoggerFactory());
        await runtime.RegisterAgentFactoryAsync("MyAgent", async (id, runtime) => await ValueTask.FromResult(new TestProtobufAgent(id, runtime, logger)));
        var agentId = new AgentId("MyAgent", "default");
        var response = await runtime.SendMessageAsync(new RpcTextMessage { Source = "TestTopic", Content = "Request" }, agentId);

        // Assert
        Assert.NotNull(response);
        Assert.IsType<RpcTextMessage>(response);
        if (response is RpcTextMessage responseString)
        {
            Assert.Equal("Request", responseString.Content);
        }
        fixture.Dispose();
    }

    public class ReceiverAgent(AgentId id,
            IAgentRuntime runtime) : BaseAgent(id, runtime, "Receiver Agent", null),
            IHandle<TextMessage>
    {
        public ValueTask HandleAsync(TextMessage item, MessageContext messageContext)
        {
            ReceivedItems.Add(item.Content);
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
        await runtime.PublishMessageAsync(new TextMessage { Source = "topic", Content = "test" }, new TopicId(topicTypeName));
        await Task.Delay(100);

        Assert.True(agent.ReceivedItems.Count == 0);

        var subscription = new TypeSubscription(topicTypeName, "MyAgent");
        await runtime.AddSubscriptionAsync(subscription);

        await runtime.PublishMessageAsync(new TextMessage { Source = "topic", Content = "test" }, new TopicId(topicTypeName));
        await Task.Delay(100);

        Assert.True(agent.ReceivedItems.Count == 1);
        Assert.Equal("test", agent.ReceivedItems[0]);

        await runtime.RemoveSubscriptionAsync(subscription.Id);
        await runtime.PublishMessageAsync(new TextMessage { Source = "topic", Content = "test" }, new TopicId(topicTypeName));
        await Task.Delay(100);

        Assert.True(agent.ReceivedItems.Count == 1);
        fixture.Dispose();
    }
}
