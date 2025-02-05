// Copyright (c) Microsoft Corporation. All rights reserved.
// AgentRuntimeTests.cs
using FluentAssertions;
using System.Text.Json;
using Microsoft.AutoGen.Contracts;
using Microsoft.Extensions.Logging;
using Xunit;

namespace Microsoft.AutoGen.Core.Tests;

[Trait("Category", "UnitV2")]
public class AgentRuntimeTests()
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
        var savedState = await runtime.SaveStateAsync();

        // Ensure saved state contains the agent's state
        savedState.Should().ContainKey(agentId.ToString());

        // Ensure the agent's state is stored as a valid JSON object
        savedState[agentId.ToString()].ValueKind.Should().Be(JsonValueKind.Object, "Agent state should be stored as a JSON object");

        // Serialize and Deserialize the state to simulate persistence
        string json = JsonSerializer.Serialize(savedState);
        json.Should().NotBeNullOrEmpty("Serialized state should not be empty");

        var deserializedState = JsonSerializer.Deserialize<IDictionary<string, JsonElement>>(json)
            ?? throw new Exception("Deserialized state is unexpectedly null");

        deserializedState.Should().ContainKey(agentId.ToString());

        // Load the saved state back into a new runtime instance
        var newRuntime = new InProcessRuntime();
        await newRuntime.StartAsync();
        await newRuntime.LoadStateAsync(deserializedState);

        // Ensure the agent exists in the new runtime
        AgentId newAgentId = await newRuntime.GetAgentAsync("MyAgent", lazy: false);
        newAgentId.Should().Be(agentId, "Loaded agent ID should match original agent ID");

        // Retrieve the agent's saved state
        var restoredState = await newRuntime.SaveAgentStateAsync(newAgentId);
        restoredState.Should().ContainKey("TestTopic");

        // Ensure "TestTopic" contains the correct message
        restoredState["TestTopic"].ValueKind.Should().Be(JsonValueKind.String, "Expected 'TestTopic' to be a string");
        restoredState["TestTopic"].GetString().Should().Be("test", "Agent state should contain the original message");
    }
}
