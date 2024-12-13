// Copyright (c) Microsoft Corporation. All rights reserved.
// AgentTests.cs

using System.Collections.Concurrent;
using FluentAssertions;
using Google.Protobuf.Reflection;
using Microsoft.AspNetCore.Builder;
using Microsoft.AutoGen.Contracts;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;
using Moq;
using Xunit;
using static Microsoft.AutoGen.Core.Tests.AgentTests;

namespace Microsoft.AutoGen.Core.Tests;

[Collection(ClusterFixtureCollection.Name)]
public class AgentTests(InMemoryAgentRuntimeFixture fixture)
{
    private readonly InMemoryAgentRuntimeFixture _fixture = fixture;

    [Fact]
    public async Task ItInvokeRightHandlerTestAsync()
    {
        var mockContext = new Mock<IAgentRuntime>();
        mockContext.SetupGet(x => x.AgentId).Returns(new AgentId("test", "test"));
        // mock SendMessageAsync
        mockContext.Setup(x => x.SendMessageAsync(It.IsAny<Message>(), It.IsAny<CancellationToken>()))
            .Returns(new ValueTask());
        var agent = new TestAgent(mockContext.Object, new EventTypes(TypeRegistry.Empty, [], []), new Logger<Agent>(new LoggerFactory()));

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
    public class TestAgent : Agent, IHandle<string>, IHandle<int>, IHandle<TextMessage>
    {
        public TestAgent(
            IAgentRuntime context,
            [FromKeyedServices("EventTypes")] EventTypes eventTypes,
            Logger<Agent>? logger = null) : base(context, eventTypes, logger)
        {
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

        public Task Handle(TextMessage item)
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

        // step 1: create in-memory agent runtime
        // step 2: register TestAgent to that agent runtime
        builder
            .AddAgentWorker()
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
