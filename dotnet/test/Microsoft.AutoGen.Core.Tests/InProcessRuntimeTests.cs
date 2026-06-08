// Copyright (c) Microsoft Corporation. All rights reserved.
// InProcessRuntimeTests.cs
using System.Text.Json;
using FluentAssertions;
using Microsoft.AutoGen.Contracts;
using Microsoft.Extensions.Logging;
using Xunit;

namespace Microsoft.AutoGen.Core.Tests;

[Trait("Category", "UnitV2")]
public class InProcessRuntimeTests()
{
    // Agent will not deliver to self will success when runtime.DeliverToSelf is false (default)
    [Fact]
    public async Task RuntimeAgentPublishToSelfDefaultNoSendTest()
    {
        var runtime = new InProcessRuntime();
        await runtime.StartAsync();

        Logger<BaseAgent> logger = new(new LoggerFactory());
        SubscribedSelfPublishAgent agent = null!;

        await runtime.RegisterAgentFactoryAsync("MyAgent", (id, runtime) =>
        {
            agent = new SubscribedSelfPublishAgent(id, runtime, logger);
            return ValueTask.FromResult(agent);
        });

        // Ensure the agent is actually created
        AgentId agentId = await runtime.GetAgentAsync("MyAgent", lazy: false);

        // Validate agent ID
        agentId.Should().Be(agent.Id, "Agent ID should match the registered agent");

        await runtime.RegisterImplicitAgentSubscriptionsAsync<SubscribedSelfPublishAgent>("MyAgent");

        var topicType = "TestTopic";

        await runtime.PublishMessageAsync("SelfMessage", new TopicId(topicType)).ConfigureAwait(true);

        await runtime.RunUntilIdleAsync();

        // Agent has default messages and could not publish to self
        agent.Text.Source.Should().Be("DefaultTopic");
        agent.Text.Content.Should().Be("DefaultContent");
    }

    // Agent delivery to self will success when runtime.DeliverToSelf is true
    [Fact]
    public async Task RuntimeAgentPublishToSelfDeliverToSelfTrueTest()
    {
        var runtime = new InProcessRuntime();
        runtime.DeliverToSelf = true;
        await runtime.StartAsync();

        Logger<BaseAgent> logger = new(new LoggerFactory());
        SubscribedSelfPublishAgent agent = null!;

        await runtime.RegisterAgentFactoryAsync("MyAgent", (id, runtime) =>
        {
            agent = new SubscribedSelfPublishAgent(id, runtime, logger);
            return ValueTask.FromResult(agent);
        });

        // Ensure the agent is actually created
        AgentId agentId = await runtime.GetAgentAsync("MyAgent", lazy: false);

        // Validate agent ID
        agentId.Should().Be(agent.Id, "Agent ID should match the registered agent");

        await runtime.RegisterImplicitAgentSubscriptionsAsync<SubscribedSelfPublishAgent>("MyAgent");

        var topicType = "TestTopic";

        await runtime.PublishMessageAsync("SelfMessage", new TopicId(topicType)).ConfigureAwait(true);

        await runtime.RunUntilIdleAsync();

        // Agent sucessfully published to self
        agent.Text.Source.Should().Be("TestTopic");
        agent.Text.Content.Should().Be("SelfMessage");
    }

    [Fact]
    public async Task RuntimeShouldSaveLoadStateCorrectlyTest()
    {
        // Create a runtime and register an agent
        var runtime = new InProcessRuntime();
        await runtime.StartAsync();
        Logger<BaseAgent> logger = new(new LoggerFactory());
        SubscribedSaveLoadAgent agent = null!;
        await runtime.RegisterAgentFactoryAsync("MyAgent", (id, runtime) =>
        {
            agent = new SubscribedSaveLoadAgent(id, runtime, logger);
            return ValueTask.FromResult(agent);
        });

        // Get agent ID and instantiate agent by publishing
        AgentId agentId = await runtime.GetAgentAsync("MyAgent", lazy: true);
        await runtime.RegisterImplicitAgentSubscriptionsAsync<SubscribedSaveLoadAgent>("MyAgent");
        var topicType = "TestTopic";
        await runtime.PublishMessageAsync(new TextMessage { Source = topicType, Content = "test" }, new TopicId(topicType)).ConfigureAwait(true);
        await runtime.RunUntilIdleAsync();
        agent.ReceivedMessages.Any().Should().BeTrue("Agent should receive messages when subscribed.");

        // Save the state
        var savedState = await runtime.SaveStateAsync();

        // Ensure calling TryGetPropertyValue with the agent's key returns the agent's state
        savedState.TryGetProperty(agentId.ToString(), out var agentState).Should().BeTrue("Agent state should be saved");

        // Ensure the agent's state is stored as a valid JSON object
        agentState.ValueKind.Should().Be(JsonValueKind.Object, "Agent state should be stored as a JSON object");

        // Serialize and Deserialize the state to simulate persistence
        string json = JsonSerializer.Serialize(savedState);
        json.Should().NotBeNullOrEmpty("Serialized state should not be empty");
        var deserializedState = JsonSerializer.Deserialize<IDictionary<string, JsonElement>>(json)
            ?? throw new Exception("Deserialized state is unexpectedly null");
        deserializedState.Should().ContainKey(agentId.ToString());

        // Start new runtime and restore the state
        var newRuntime = new InProcessRuntime();
        await newRuntime.StartAsync();
        await newRuntime.RegisterAgentFactoryAsync("MyAgent", (id, runtime) =>
        {
            agent = new SubscribedSaveLoadAgent(id, runtime, logger);
            return ValueTask.FromResult(agent);
        });
        await newRuntime.RegisterImplicitAgentSubscriptionsAsync<SubscribedSaveLoadAgent>("MyAgent");

        // Show that no agent instances exist in the new runtime
        newRuntime.agentInstances.Count.Should().Be(0, "Agent should be registered in the new runtime");

        // Load the state into the new runtime and show that agent is now instantiated
        await newRuntime.LoadStateAsync(savedState);
        newRuntime.agentInstances.Count.Should().Be(1, "Agent should be registered in the new runtime");
        newRuntime.agentInstances.Should().ContainKey(agentId, "Agent should be loaded into the new runtime");
    }
}
