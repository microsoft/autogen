// Copyright (c) Microsoft Corporation. All rights reserved.
// RegistryTests.cs

using System.Collections.Concurrent;
using Microsoft.AutoGen.Contracts;
using Microsoft.Extensions.Logging;
using Moq;
using Xunit;

namespace Microsoft.AutoGen.Core.Tests;

public class RegistryTests
{
    private readonly Mock<IRegistryStorage> _storageMock;
    private readonly Mock<ILogger<Registry>> _loggerMock;
    private readonly Registry _registry;

    public RegistryTests()
    {
        _storageMock = new Mock<IRegistryStorage>();
        _loggerMock = new Mock<ILogger<Registry>>();
        _storageMock.Setup(s => s.ReadStateAsync(It.IsAny<CancellationToken>())).ReturnsAsync(new AgentsRegistryState());
        _registry = new Registry(_storageMock.Object, _loggerMock.Object);
    }

    [Fact]
    public async Task GetSubscribedAndHandlingAgentsAsync_ShouldReturnEmptyList_WhenNoAgentsSubscribed()
    {
        // Arrange
        var state = new AgentsRegistryState
        {
            TopicToAgentTypesMap = new ConcurrentDictionary<string, HashSet<string>>()
        };
        _storageMock.Setup(s => s.ReadStateAsync(CancellationToken.None)).ReturnsAsync(state);

        // Act
        var agents = await _registry.GetSubscribedAndHandlingAgentsAsync("topic", "eventType");

        // Assert
        Assert.Empty(agents);
    }

    [Fact]
    public async Task GetSubscribedAndHandlingAgentsAsync_ShouldReturnAgents_WhenAgentsSubscribed()
    {
        // Arrange
        var agent1 = "agent1";
        var agent2 = "agent2";
        var topic = "topic";
        var request = new AddSubscriptionRequest
        {
            Subscription = new Subscription
            {
                TypeSubscription = new TypeSubscription
                {
                    AgentType = agent1,
                    TopicType = topic
                }
            }
        };
        await _registry.SubscribeAsync(request);
        request.Subscription.TypeSubscription.AgentType = agent2;
        await _registry.SubscribeAsync(request);

        // Act
        var agents = await _registry.GetSubscribedAndHandlingAgentsAsync(topic, "eventType");

        // Assert
        Assert.Equal(2, agents.Count);
        Assert.Contains(agent1, agents);
        Assert.Contains(agent2, agents);
    }

    [Fact]
    public async Task RegisterAgentTypeAsync_ShouldAddAgentType()
    {
        // Arrange
        var agentTypeName = "TestAgent";
        var agentType = Type.GetType(agentTypeName);

        var request = new RegisterAgentTypeRequest { Type = agentTypeName };
        var fixture = new InMemoryAgentRuntimeFixture();
        var (runtime, agent) = fixture.Start();

        // Act
        await _registry.RegisterAgentTypeAsync(request, runtime);

        // Assert
        _storageMock.Verify(s => s.WriteStateAsync(It.IsAny<AgentsRegistryState>(), It.IsAny<CancellationToken>()), Times.Once);
        Assert.Contains(agentTypeName, _registry.State.AgentTypes.Keys);
        fixture.Stop();
    }

    [Fact]
    public async Task SubscribeAsync_ShouldAddSubscription()
    {
        // Arrange
        var request = new AddSubscriptionRequest
        {
            Subscription = new Subscription
            {
                TypeSubscription = new TypeSubscription
                {
                    AgentType = "TestAgent",
                    TopicType = "TestTopic"
                }
            }
        };

        // Act
        await _registry.SubscribeAsync(request);

        // Assert
        _storageMock.Verify(s => s.WriteStateAsync(It.IsAny<AgentsRegistryState>(), It.IsAny<CancellationToken>()), Times.Once);
        Assert.Contains("TestAgent", _registry.State.AgentsToTopicsMap.Keys);
        Assert.Contains("TestTopic", _registry.State.TopicToAgentTypesMap.Keys);
    }

    [Fact]
    public async Task UnsubscribeAsync_ShouldFail_WhenRequestIsInvalid()
    {
        // Arrange
        var request = new RemoveSubscriptionRequest { Id = "invalid-guid" };

        // Act
        var exception = await Assert.ThrowsAsync<InvalidOperationException>(async () => await _registry.UnsubscribeAsync(request).AsTask());
    }

    [Fact]
    public async Task UnsubscribeAsync_ShouldRemoveSubscription()
    {
        // Arrange
        var topic = "TestTopic1";
        var agent = "TestAgent1";
        var request = new AddSubscriptionRequest
        {
            Subscription = new Subscription
            {
                TypeSubscription = new TypeSubscription
                {
                    AgentType = agent,
                    TopicType = topic
                }
            }
        };
        await _registry.SubscribeAsync(request);
        var subscriptions = await _registry.GetSubscriptionsAsync(new GetSubscriptionsRequest());
        var subscriptionId = subscriptions.Where(
            s => s.TypeSubscription.AgentType == agent && s.TypeSubscription.TopicType == topic
            ).Select(s => s.Id).FirstOrDefault();
        var removeRequest = new RemoveSubscriptionRequest { Id = subscriptionId };

        //Act
        await _registry.UnsubscribeAsync(removeRequest);
        subscriptions = await _registry.GetSubscriptionsAsync(new GetSubscriptionsRequest());

        // Assert subscriptions doesn't match for id
        Assert.DoesNotContain(subscriptionId, subscriptions.Select(s => s.Id));
    }
}
