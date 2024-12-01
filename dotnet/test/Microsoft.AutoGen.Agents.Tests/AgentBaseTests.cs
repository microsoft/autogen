// Copyright (c) Microsoft Corporation. All rights reserved.
// AgentBaseTests.cs

using System.Collections.Concurrent;
using System.Diagnostics;
using FluentAssertions;
using Google.Protobuf.Reflection;
using Microsoft.AspNetCore.Builder;
using Microsoft.AutoGen.Abstractions;
using Microsoft.AutoGen.Core;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;
using Moq;
using Tests.Events;
using Xunit;
using static Microsoft.AutoGen.Agents.Tests.AgentBaseTests;

namespace Microsoft.AutoGen.Agents.Tests;

[Collection(ClusterFixtureCollection.Name)]
public class AgentBaseTests(InMemoryAgentRuntimeFixture fixture)
{
    private readonly InMemoryAgentRuntimeFixture _fixture = fixture;

    [Fact]
    public async Task ItInvokeRightHandlerTestAsync()
    {
        var agentWorker = _fixture.AppHost.Services.GetRequiredService<IAgentWorker>();
        var dctx = Mock.Of<DistributedContextPropagator>();
        var logger = Mock.Of<ILogger<AgentBase>>();
        var context = new RuntimeContext(new AgentId { Type = "test", Key = "test" }, agentWorker, logger, dctx);
        var agent = new TestAgent(context, new EventTypes(TypeRegistry.Empty, [], []));
        await agent.Handle(new TextMessage { Source = "test", TextMessage_ = "Wow" }, CancellationToken.None);

        TestAgent.ReceivedMessages.Count.Should().Be(1);
        TestAgent.ReceivedMessages["test"].Should().Be("Wow");

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
    public class TestAgent : AgentBase, IHandle<TextMessage>
    {
        public TestAgent(
            RuntimeContext context,
            [FromKeyedServices("EventTypes")] EventTypes eventTypes,
            Logger<AgentBase>? logger = null) : base(context, eventTypes, logger)
        {
        }

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
        var builder = WebApplication.CreateSlimBuilder(new WebApplicationOptions { });

        // step 1: create in-memory agent runtime
        // step 2: register TestAgent to that agent runtime
        builder
            .AddInMemoryWorker()
            .AddAgentHost()
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
