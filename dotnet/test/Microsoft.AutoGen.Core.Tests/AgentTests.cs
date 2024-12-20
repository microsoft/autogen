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

    [Fact]
    public void Agent_ShouldThrowException_WhenNotInitialized()
    {
        var agent = ActivatorUtilities.CreateInstance<TestAgent>(_serviceProvider);
        agent.Subscribe("TestEvent");
        Assert.Throws<UninitializedAgentWorker.AgentInitalizedIncorrectlyException>(() => agent.Worker.ServiceProvider);
    }
    [Fact]
    public async Task ItInvokeRightHandlerTestAsync()
    {
        var agent = new TestAgent(new AgentsMetadata(TypeRegistry.Empty, new Dictionary<string, Type>(), new Dictionary<Type, HashSet<string>>(), new Dictionary<Type, HashSet<string>>()), new Logger<Agent>(new LoggerFactory()));

        await agent.HandleObject("hello world");
        await agent.HandleObject(42);

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
