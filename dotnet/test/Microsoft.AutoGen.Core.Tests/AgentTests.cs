// Copyright (c) Microsoft Corporation. All rights reserved.
// AgentTests.cs

using System.Collections.Concurrent;
using System.Diagnostics;
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
        var agent = ActivatorUtilities.CreateInstance<TestAgent>(_serviceProvider);
        var worker = _serviceProvider.GetRequiredService<IAgentWorker>();
        Agent.Initialize(worker, agent);
        Assert.Equal("AgentWorker", agent.Worker.GetType().Name);
        var subscriptions = await agent.GetSubscriptionsAsync();
        Assert.Equal(2, subscriptions.Count);
    }
    /// <summary>
    /// Test SubscribeAsync method
    /// </summary>
    /// <returns>void</returns>
    [Fact]
    public async Task SubscribeAsync_UnsubscribeAsync_and_GetSubscriptionsTest()
    {
        var agent = ActivatorUtilities.CreateInstance<TestAgent>(_serviceProvider);
        var worker = _serviceProvider.GetRequiredService<IAgentWorker>();
        Agent.Initialize(worker, agent);
        var subscriptions = await agent.GetSubscriptionsAsync().ConfigureAwait(true);
        Assert.Equal(2, subscriptions.Count);
        await agent.SubscribeAsync("TestEvent");
        subscriptions = await agent.GetSubscriptionsAsync().ConfigureAwait(true);
        Assert.Equal(3, subscriptions.Count);
        await agent.UnsubscribeAsync("TestEvent");
        subscriptions = await agent.GetSubscriptionsAsync().ConfigureAwait(true);
        Assert.Equal(2, subscriptions.Count);
    }

    [Fact]
    public async Task ItInvokeRightHandlerTestAsync()
    {
        var agent = new TestAgent(new AgentsMetadata(TypeRegistry.Empty, new Dictionary<string, Type>(), new Dictionary<Type, HashSet<string>>(), new Dictionary<Type, HashSet<string>>()), new Logger<Agent>(new LoggerFactory()));

        await agent.HandleObjectAsync("hello world");
        await agent.HandleObjectAsync(42);

        agent.ReceivedItems.Should().HaveCount(2);
        agent.ReceivedItems[0].Should().Be("hello world");
        agent.ReceivedItems[1].Should().Be(42);
    }

    [Fact]
    public async Task ItDelegateMessageToTestAgentAsync()
    {
        var client = _fixture.AppHost.Services.GetRequiredService<Client>();
        await client.PublishMessageAsync(new TextMessage()
        {
            Source = nameof(ItDelegateMessageToTestAgentAsync),
            TextMessage_ = "buffer"
        }, token: CancellationToken.None);

        // wait for 10 seconds
        var cts = new CancellationTokenSource(TimeSpan.FromSeconds(10));
        while (!TestAgent.ReceivedMessages.ContainsKey(nameof(ItDelegateMessageToTestAgentAsync)) && !cts.Token.IsCancellationRequested)
        {
            await Task.Delay(100);
        }

        TestAgent.ReceivedMessages[nameof(ItDelegateMessageToTestAgentAsync)].Should().NotBeNull();
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

public sealed class InMemoryAgentRuntimeFixture : IDisposable
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

    void IDisposable.Dispose()
    {
        AppHost.StopAsync().Wait();
        AppHost.Dispose();
    }
}

[CollectionDefinition(Name)]
public sealed class ClusterFixtureCollection : ICollectionFixture<InMemoryAgentRuntimeFixture>
{
    public const string Name = nameof(ClusterFixtureCollection);
}
