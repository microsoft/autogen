// Copyright (c) Microsoft Corporation. All rights reserved.
// AgentTests.cs

using System.Collections.Concurrent;
using System.Diagnostics;
using System.Text.Json;
using FluentAssertions;
using Google.Protobuf.Reflection;
using Microsoft.AspNetCore.Builder;
using Microsoft.AutoGen.Contracts;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.DependencyInjection.Extensions;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;
using Xunit;
using static Microsoft.AutoGen.Core.Tests.AgentTests;

namespace Microsoft.AutoGen.Core.Tests;

[Collection(ClusterFixtureCollection.Name)]
public class AgentTests(InMemoryAgentRuntimeFixture fixture)
{
    private readonly IServiceProvider _serviceProvider = fixture.AppHost.Services;
    private readonly InMemoryAgentRuntimeFixture _fixture = fixture;
    // need a variable to store the runtime instance
    public static WebApplication? Host { get; private set; }

    /// <summary>
    /// Verify that if the agent is not initialized via AgentWorker, it should throw the correct exception.
    /// </summary>
    /// <returns>void</returns>
    [Fact]
    public async Task Agent_ShouldThrowException_WhenNotInitialized()
    {
        var agent = ActivatorUtilities.CreateInstance<TestAgent>(_serviceProvider);
        await Assert.ThrowsAsync<UninitializedAgentWorker.AgentInitalizedIncorrectlyException>(
            async () =>
            {
                await agent.SubscribeAsync("TestEvent");
            }
        );
    }

    /// <summary>
    /// validate that the agent is initialized correctly with implicit subs
    /// </summary>
    /// <returns>void</returns>
    [Fact]
    public async Task Agent_ShouldInitializeCorrectly()
    {
        var (worker, agent) = _fixture.Start();
        Assert.Equal("AgentWorker", worker.GetType().Name);
        var subscriptions = await agent.GetSubscriptionsAsync();
        Assert.Equal(2, subscriptions.Count);
        _fixture.Stop();
    }
    /// <summary>
    /// Test SubscribeAsync method
    /// </summary>
    /// <returns>void</returns>
    [Fact]
    public async Task SubscribeAsync_UnsubscribeAsync_and_GetSubscriptionsTest()
    {
        var (_, agent) = _fixture.Start();
        await agent.SubscribeAsync("TestEvent");
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
        await agent.UnsubscribeAsync("TestEvent").ConfigureAwait(true);
        await Task.Delay(500);
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
        _fixture.Stop();
    }

    /// <summary>
    /// Test StoreAsync and ReadAsync methods
    /// </summary>
    /// <returns>void</returns>
    [Fact]
    public async Task StoreAsync_and_ReadAsyncTest()
    {
        var (_, agent) = _fixture.Start();
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
        _fixture.Stop();
    }

    /// <summary>
    /// Test PublishMessageAsync method and ReceiveMessage method
    /// </summary>
    /// <returns>void</returns>
    [Fact]
    public async Task PublishMessageAsync_and_ReceiveMessageTest()
    {
        var (_, agent) = _fixture.Start();
        await agent.SubscribeAsync("TestEvent").ConfigureAwait(true);
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
        await agent.PublishMessageAsync(new TextMessage()
        {
            Source = "TestEvent",
            TextMessage_ = "buffer"
        }).ConfigureAwait(true);
        await Task.Delay(100);
        Assert.True(TestAgent.ReceivedMessages.ContainsKey("TestEvent"));
        _fixture.Stop();
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

    [Fact]
    public async Task DelegateMessageToTestAgentAsync()
    {
        var client = _fixture.AppHost.Services.GetRequiredService<Client>();
        await client.PublishMessageAsync(new TextMessage()
        {
            Source = nameof(DelegateMessageToTestAgentAsync),
            TextMessage_ = "buffer"
        }, token: CancellationToken.None);

        // wait for 10 seconds
        var cts = new CancellationTokenSource(TimeSpan.FromSeconds(10));
        while (!TestAgent.ReceivedMessages.ContainsKey(nameof(DelegateMessageToTestAgentAsync)) && !cts.Token.IsCancellationRequested)
        {
            await Task.Delay(100);
        }

        TestAgent.ReceivedMessages[nameof(DelegateMessageToTestAgentAsync)].Should().NotBeNull();
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
/// InMemoryAgentRuntimeFixture - provides a fixture for the agent runtime.
/// </summary>
/// <remarks>
/// This fixture is used to provide a runtime for the agent tests.
/// However, it is shared between tests. So operations from one test can affect another.
/// </remarks>
public sealed class InMemoryAgentRuntimeFixture
{
    public InMemoryAgentRuntimeFixture()
    {
        var builder = WebApplication.CreateBuilder();
        builder.Services.TryAddSingleton(DistributedContextPropagator.Current);
        builder.AddAgentWorker()
            .AddAgent<TestAgent>(nameof(TestAgent));
        AppHost = builder.Build();
        AppHost.StartAsync().Wait();
    }
    public IHost AppHost { get; }

    /// <summary>
    /// Start - starts the agent
    /// </summary>
    /// <returns>IAgentWorker, TestAgent</returns>
    public (IAgentWorker, TestAgent) Start()
    {
        var agent = ActivatorUtilities.CreateInstance<TestAgent>(AppHost.Services);
        var worker = AppHost.Services.GetRequiredService<IAgentWorker>();
        Agent.Initialize(worker, agent);
        return (worker, agent);
    }
    /// <summary>
    /// Stop - stops the agent
    /// </summary>
    /// <returns>void</returns>
    public void Stop()
    {
        IHostApplicationLifetime hostApplicationLifetime = AppHost.Services.GetRequiredService<IHostApplicationLifetime>();
        hostApplicationLifetime.StopApplication();
    }
}

[CollectionDefinition(Name)]
public sealed class ClusterFixtureCollection : ICollectionFixture<InMemoryAgentRuntimeFixture>
{
    public const string Name = nameof(ClusterFixtureCollection);
}
