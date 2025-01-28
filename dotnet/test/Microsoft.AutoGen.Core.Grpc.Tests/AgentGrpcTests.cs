// Copyright (c) Microsoft Corporation. All rights reserved.
// AgentGrpcTests.cs

using System.Collections.Concurrent;
using System.Text.Json;
using FluentAssertions;
using Google.Protobuf.Reflection;
using Microsoft.AutoGen.Contracts;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;
using Xunit;
using static Microsoft.AutoGen.Core.Grpc.Tests.AgentGrpcTests;

namespace Microsoft.AutoGen.Core.Grpc.Tests;

public class AgentGrpcTests
{
    /// <summary>
    /// Verify that if the agent is not initialized via AgentWorker, it should throw the correct exception.
    /// </summary>
    /// <returns>void</returns>
    [Fact]
    public async Task Agent_ShouldThrowException_WhenNotInitialized()
    {
        using var runtime = new GrpcRuntime();
        var (_, agent) = runtime.Start(false); // Do not initialize

        // Expect an exception when calling AddSubscriptionAsync because the agent is uninitialized
        await Assert.ThrowsAsync<UninitializedAgentWorker.AgentInitalizedIncorrectlyException>(
            async () => await agent.AddSubscriptionAsync("TestEvent")
        );
    }

    /// <summary>
    /// validate that the agent is initialized correctly with implicit subs
    /// </summary>
    /// <returns>void</returns>
    [Fact]
    public async Task Agent_ShouldInitializeCorrectly()
    {
        using var runtime = new GrpcRuntime();
        var (worker, agent) = runtime.Start();
        Assert.Equal(nameof(GrpcAgentRuntime), worker.GetType().Name);
        await Task.Delay(5000);
        var subscriptions = await agent.GetSubscriptionsAsync();
        Assert.Equal(2, subscriptions.Count);
    }
    /// <summary>
    /// Test AddSubscriptionAsync method
    /// </summary>
    /// <returns>void</returns>
    [Fact]
    public async Task SubscribeAsync_UnsubscribeAsync_and_GetSubscriptionsTest()
    {
        using var runtime = new GrpcRuntime();
        var (_, agent) = runtime.Start();
        await agent.AddSubscriptionAsync("TestEvent");
        await Task.Delay(100);
        var subscriptions = await agent.GetSubscriptionsAsync().ConfigureAwait(true);
        var found = false;
        foreach (var subscription in subscriptions)
        {
            if (subscription.TypeSubscription.TopicType == "TestEvent")
            {
                found = true;
            }
        }
        Assert.True(found);
        await agent.RemoveSubscriptionAsync("TestEvent").ConfigureAwait(true);
        await Task.Delay(1000);
        subscriptions = await agent.GetSubscriptionsAsync().ConfigureAwait(true);
        found = false;
        foreach (var subscription in subscriptions)
        {
            if (subscription.TypeSubscription.TopicType == "TestEvent")
            {
                found = true;
            }
        }
        Assert.False(found);
    }

    /// <summary>
    /// Test StoreAsync and ReadAsync methods
    /// </summary>
    /// <returns>void</returns>
    [Fact]
    public async Task StoreAsync_and_ReadAsyncTest()
    {
        using var runtime = new GrpcRuntime();
        var (_, agent) = runtime.Start();
        Dictionary<string, string> state = new()
        {
            { "testdata", "Active" }
        };
        await agent.StoreAsync(new AgentState
        {
            AgentId = agent.AgentId,
            TextData = JsonSerializer.Serialize(state)
        }).ConfigureAwait(true);
        var readState = await agent.ReadAsync<AgentState>(agent.AgentId).ConfigureAwait(true);
        var read = JsonSerializer.Deserialize<Dictionary<string, string>>(readState.TextData) ?? new Dictionary<string, string> { { "data", "No state data found" } };
        read.TryGetValue("testdata", out var value);
        Assert.Equal("Active", value);
    }

    /// <summary>
    /// Test PublishMessageAsync method and ReceiveMessage method
    /// </summary>
    /// <returns>void</returns>
    [Fact]
    public async Task PublishMessageAsync_and_ReceiveMessageTest()
    {
        using var runtime = new GrpcRuntime();
        var (_, agent) = runtime.Start();
        var topicType = "TestTopic";
        await agent.AddSubscriptionAsync(topicType).ConfigureAwait(true);
        var subscriptions = await agent.GetSubscriptionsAsync().ConfigureAwait(true);
        var found = false;
        foreach (var subscription in subscriptions)
        {
            if (subscription.TypeSubscription.TopicType == topicType)
            {
                found = true;
            }
        }
        Assert.True(found);
        await agent.PublishMessageAsync(new TextMessage()
        {
            Source = topicType,
            TextMessage_ = "buffer"
        }, topicType).ConfigureAwait(true);
        await Task.Delay(100);
        Assert.True(TestAgent.ReceivedMessages.ContainsKey(topicType));
        runtime.Stop();
    }

    [Fact]
    public async Task InvokeCorrectHandler()
    {
        var agent = new TestAgent(new AgentsMetadata(TypeRegistry.Empty, new Dictionary<string, Type>(), new Dictionary<Type, HashSet<string>>(), new Dictionary<Type, HashSet<string>>()), new Logger<Agent>(new LoggerFactory()));

        await agent.HandleObjectAsync("hello world");
        await agent.HandleObjectAsync(42);

        agent.ReceivedItems.Should().HaveCount(2);
        agent.ReceivedItems[0].Should().Be("hello world");
        agent.ReceivedItems[1].Should().Be(42);
    }

    /// <summary>
    /// The test agent is a simple agent that is used for testing purposes.
    /// </summary>
    public class TestAgent(
        [FromKeyedServices("AgentsMetadata")] AgentsMetadata eventTypes,
        Logger<Agent>? logger = null) : Agent(eventTypes, logger), IHandle<TextMessage>
    {
        public Task Handle(TextMessage item, CancellationToken cancellationToken = default)
        {
            ReceivedMessages[item.Source] = item.TextMessage_;
            return Task.CompletedTask;
        }
        public Task Handle(string item)
        {
            ReceivedItems.Add(item);
            return Task.CompletedTask;
        }
        public Task Handle(int item)
        {
            ReceivedItems.Add(item);
            return Task.CompletedTask;
        }
        public List<object> ReceivedItems { get; private set; } = [];

        /// <summary>
        /// Key: source
        /// Value: message
        /// </summary>
        public static ConcurrentDictionary<string, object> ReceivedMessages { get; private set; } = new();
    }
}

/// <summary>
/// GrpcRuntimeFixture - provides a fixture for the agent runtime.
/// </summary>
/// <remarks>
/// This fixture is used to provide a runtime for the agent tests.
/// However, it is shared between tests. So operations from one test can affect another.
/// </remarks>
public sealed class GrpcRuntime : IDisposable
{
    public IHost Client { get; private set; }
    public IHost? AppHost { get; private set; }

    public GrpcRuntime()
    {
        Environment.SetEnvironmentVariable("ASPNETCORE_ENVIRONMENT", "Development");
        AppHost = Host.CreateDefaultBuilder().Build();
        Client = Host.CreateDefaultBuilder().Build();
    }

    private static int GetAvailablePort()
    {
        using var listener = new System.Net.Sockets.TcpListener(System.Net.IPAddress.Loopback, 0);
        listener.Start();
        int port = ((System.Net.IPEndPoint)listener.LocalEndpoint).Port;
        listener.Stop();
        return port;
    }

    private static async Task<IHost> StartClientAsync()
    {
        return await AgentsApp.StartAsync().ConfigureAwait(false);
    }
    private static async Task<IHost> StartAppHostAsync()
    {
        return await Microsoft.AutoGen.Runtime.Grpc.Host.StartAsync(local: false, useGrpc: true).ConfigureAwait(false);

    }

    /// <summary>
    /// Start - gets a new port and starts fresh instances
    /// </summary>
    public (IAgentRuntime, TestAgent) Start(bool initialize = true)
    {
        int port = GetAvailablePort(); // Get a new port per test run

        // Update environment variables so each test runs independently
        Environment.SetEnvironmentVariable("ASPNETCORE_HTTPS_PORTS", port.ToString());
        Environment.SetEnvironmentVariable("AGENT_HOST", $"https://localhost:{port}");

        AppHost = StartAppHostAsync().GetAwaiter().GetResult();
        Client = StartClientAsync().GetAwaiter().GetResult();

        var agent = ActivatorUtilities.CreateInstance<TestAgent>(Client.Services);
        var worker = Client.Services.GetRequiredService<IAgentRuntime>();
        if (initialize)
        {
            Agent.Initialize(worker, agent);
        }

        return (worker, agent);
    }

    /// <summary>
    /// Stop - stops the agent and ensures cleanup
    /// </summary>
    public void Stop()
    {
        Client?.StopAsync().GetAwaiter().GetResult();
        AppHost?.StopAsync().GetAwaiter().GetResult();
    }

    /// <summary>
    /// Dispose - Ensures cleanup after each test
    /// </summary>
    public void Dispose()
    {
        Stop();
    }
}
