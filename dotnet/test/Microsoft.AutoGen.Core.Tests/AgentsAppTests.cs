// Copyright (c) Microsoft Corporation. All rights reserved.
// AgentsAppTests.cs
using FluentAssertions;
using Microsoft.AutoGen.Contracts;
using Microsoft.Extensions.DependencyInjection.Extensions;
using Xunit;

// Type alias for function delegate
using ModifyF = System.Func<int, int>;
using TerminationF = System.Func<int, bool>;

namespace Microsoft.AutoGen.Core.Tests;

[Trait("Category", "UnitV2")]
public class AgentsAppTests()
{
    [Fact]
    public async Task Test_AgentsAppBuilder_BuildWithoutRuntime_ThrowsException()
    {
        var builder = new AgentsAppBuilder();
        await Assert.ThrowsAsync<InvalidOperationException>(async () => await builder.BuildAsync());
    }

    [Fact]
    public async Task Test_AgentsAppBuilder_BuildAndRun_Successfully()
    {
        var builder = new AgentsAppBuilder().UseInProcessRuntime();
        var app = await builder.BuildAsync();

        Assert.NotNull(app);
        Assert.NotNull(app.Services);
        Assert.NotNull(app.AgentRuntime);

        await app.StartAsync();
        await Assert.ThrowsAsync<InvalidOperationException>(async () => await app.StartAsync());

        await app.ShutdownAsync();

        // Check that app has stopped
        Assert.Equal(0, typeof(AgentsApp)
            .GetField("runningCount", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance)?
            .GetValue(app));
    }

    [Fact]
    public async Task Test_AgentsApp_PublishMessageAsync_SuccessfullyPublishes()
    {
        var builder = new AgentsAppBuilder().UseInProcessRuntime();
        var app = await builder.BuildAsync();

        await app.StartAsync();

        var topic = new TopicId("TestTopic");
        await app.PublishMessageAsync("TestMessage", topic);

        await app.ShutdownAsync();
    }

    [Fact]
    public void Test_AgentsAppBuilder_AddAgentsFromAssemblies_DoesNotThrow()
    {
        var builder = new AgentsAppBuilder().UseInProcessRuntime();
        builder.AddAgentsFromAssemblies(AppDomain.CurrentDomain.GetAssemblies());

        Assert.NotNull(builder);
    }

    [Fact]
    public async Task Test_AgentsApp_PublishMessage_SingleAgent_ReceivesMessage()
    {
        // Define the functions
        ModifyF modifyFunc = (int x) => x - 1;
        TerminationF runUntilFunc = (int x) => x <= 1;

        // Create and configure the application
        var appBuilder = new AgentsAppBuilder().UseInProcessRuntime();

        // Add some dummy services
        appBuilder.Services.TryAddSingleton(modifyFunc);
        appBuilder.Services.TryAddSingleton(runUntilFunc);

        // Register a single agent
        appBuilder.AddAgent<SubscribedAgent>("TestAgent");

        var app = await appBuilder.BuildAsync();
        await app.StartAsync();

        // Publish a message
        var initialMessage = new TextMessage { Source = "Hello", Content = "World" };
        await app.PublishMessageAsync(initialMessage, new TopicId("TestTopic"));

        // Give time for message processing
        await Task.Delay(100);

        // Validate that the agent received the message
        var agentId = await app.AgentRuntime.GetAgentAsync("TestAgent", lazy: false);
        Assert.Equal("TestAgent", agentId.Type);

        var ipr = app.AgentRuntime as InProcessRuntime;
        ipr.Should().NotBeNull("InProcessRuntime should be available.");
        ipr!.agentInstances.Should().NotBeEmpty("Agent should be registered in the runtime.");

        // Ensure agent exists before accessing it
        ipr.agentInstances.Should().ContainKey(agentId, "Agent should be present in the runtime.");
        var subscribedAgent = ipr.agentInstances[agentId] as SubscribedAgent;
        subscribedAgent.Should().NotBeNull("Agent should exist and be a SubscribedAgent.");

        // Verify received messages
        subscribedAgent!.ReceivedMessages[initialMessage.Source].Should().Be(initialMessage.Content, "Message content should match.");

        await app.ShutdownAsync();
    }
}
