// Copyright (c) Microsoft Corporation. All rights reserved.
// AgentBaseTests.cs

using System.Collections.Concurrent;
using System.Diagnostics;
using FluentAssertions;
using Google.Protobuf.Reflection;
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
        var logger = Mock.Of<ILogger<Agent>>();
        var context = new RuntimeContext(new AgentId { Type = "test", Key = "test" }, agentWorker, logger, dctx);
        var agent = new TestAgent(new EventTypes(TypeRegistry.Empty, [], []));
        Agent.Initialize(context, agent);
        await agent.Handle(new TextMessage { Source = "test", TextMessage_ = "Wow" }, CancellationToken.None);

        TestAgent.ReceivedMessages.Count.Should().Be(1);
        TestAgent.ReceivedMessages["test"].Should().Be("Wow");
    }

    [Fact]
    public async Task ItDelegateMessageToTestAgentAsync()
    {
        var client = _fixture.AppHost.Services.GetRequiredService<Client>();

        await client.PublishEventAsync(new TextMessage()
        {
            Source = nameof(ItDelegateMessageToTestAgentAsync),
            TextMessage_ = "buffer"
        }, nameof(ItDelegateMessageToTestAgentAsync), token: CancellationToken.None);

        // wait for 10 seconds
        var cts = new CancellationTokenSource(TimeSpan.FromSeconds(10));
        while (!TestAgent.ReceivedMessages.ContainsKey(nameof(ItDelegateMessageToTestAgentAsync)) && !cts.Token.IsCancellationRequested)
        {
            await Task.Delay(100);
        }

        TestAgent.ReceivedMessages[nameof(ItDelegateMessageToTestAgentAsync)].Should().NotBeNull();
    }

    [Fact]
    public async Task ItDelegateRpcMessageToTestAgentAsync()
    {
        var client = _fixture.AppHost.Services.GetRequiredService<Client>();
        await client.PublishEventAsync(new TextMessage { TextMessage_="wow" }.ToCloudEvent("mysource"), token: CancellationToken.None);
        // wait for 10 seconds
        var cts = new CancellationTokenSource(TimeSpan.FromSeconds(10));
        while (!TestAgent.ReceivedMessages.ContainsKey(nameof(ItDelegateRpcMessageToTestAgentAsync)) && !cts.Token.IsCancellationRequested)
        {
            await Task.Delay(100);
        }
        TestAgent.ReceivedMessages[nameof(ItDelegateRpcMessageToTestAgentAsync)].Should().NotBeNull();
    }

    [Fact]
    // This test will test HandleRpcMessage of the AgentBase class, sending  Request message to the TestAgent
    public async Task ItDelegateRpcRequestToTestAgentAsync()
    {
        var client = _fixture.AppHost.Services.GetRequiredService<Client>();
        var request = new RpcRequest
        {
            RequestId = Guid.NewGuid().ToString(),
            Method = "Handle",
            Source = new AgentId { Type = "", Key = "" }
        };
        //await client.SendRequestAsync(request, token: CancellationToken.None);
        // wait for 10 seconds
        var cts = new CancellationTokenSource(TimeSpan.FromSeconds(10));
        while (!TestAgent.ReceivedMessages.ContainsKey(nameof(ItDelegateRpcRequestToTestAgentAsync)) && !cts.Token.IsCancellationRequested)
        {
            await Task.Delay(100);
        }
        TestAgent.ReceivedMessages[nameof(ItDelegateRpcRequestToTestAgentAsync)].Should().NotBeNull();
    }

    [Fact]
    public async Task ItDelegateRpcResponseToTestAgentAsync()
    {
        var client = _fixture.AppHost.Services.GetRequiredService<Client>();
        var request = new RpcRequest
        {
            RequestId = Guid.NewGuid().ToString(),
            Method = "Handle",
            //Arguments = Any.Pack(new TextMessage { Source = nameof(ItDelegateRpcResponseToTestAgentAsync), TextMessage_ = "buffer" })
        };
        //await client.SendRequestAsync(request, token: CancellationToken.None);
        // wait for 10 seconds
        var cts = new CancellationTokenSource(TimeSpan.FromSeconds(10));
        while (!TestAgent.ReceivedMessages.ContainsKey(nameof(ItDelegateRpcResponseToTestAgentAsync)) && !cts.Token.IsCancellationRequested)
        {
            await Task.Delay(100);
        }
        TestAgent.ReceivedMessages[nameof(ItDelegateRpcResponseToTestAgentAsync)].Should().NotBeNull();
    }

    [Fact]
    // This function is testing the CallHandler method of the AgentBase class, when the TestAgent is handling the supplied type of CloudEvent and has the corresponding AgentId.Key
    public async Task ItDelegateCloudEventToTestAgentAsync()
    {
        var client = _fixture.AppHost.Services.GetRequiredService<Client>();
        await client.PublishEventAsync(new CloudEvent
        {
            Source = nameof(ItDelegateCloudEventToTestAgentAsync),
            //Data = Any.Pack(new TextMessage { Source = nameof(ItDelegateCloudEventToTestAgentAsync), TextMessage_ = "buffer" })
        }, token: CancellationToken.None);
        // wait for 10 seconds
        var cts = new CancellationTokenSource(TimeSpan.FromSeconds(10));
        while (!TestAgent.ReceivedMessages.ContainsKey(nameof(ItDelegateCloudEventToTestAgentAsync)) && !cts.Token.IsCancellationRequested)
        {
            await Task.Delay(100);
        }
        TestAgent.ReceivedMessages[nameof(ItDelegateCloudEventToTestAgentAsync)].Should().NotBeNull();
    }

    [Fact]
    // This function is testing the CallHandler method of the AgentBase class, when the TestAgent is handling the supplied type of CloudEvent and has a different AgentId.Key
    public async Task ItNotDelegateCloudEventToTestAgentAsync()
    {
        var client = _fixture.AppHost.Services.GetRequiredService<Client>();
        await client.PublishEventAsync(new CloudEvent
        {
            Source = nameof(ItNotDelegateCloudEventToTestAgentAsync),
           // Data = Any.Pack(new TextMessage { Source = nameof(ItNotDelegateCloudEventToTestAgentAsync), TextMessage_ = "buffer" })
        }, token: CancellationToken.None);
        // wait for 10 seconds
        var cts = new CancellationTokenSource(TimeSpan.FromSeconds(10));
        while (!TestAgent.ReceivedMessages.ContainsKey(nameof(ItNotDelegateCloudEventToTestAgentAsync)) && !cts.Token.IsCancellationRequested)
        {
            await Task.Delay(100);
        }
        TestAgent.ReceivedMessages[nameof(ItNotDelegateCloudEventToTestAgentAsync)].Should().BeNull();
    }

    /// <summary>
    /// The test agent is a simple agent that is used for testing purposes.
    /// </summary>
    public class TestAgent : Agent, IHandle<TextMessage>
    {
        public TestAgent(
            [FromKeyedServices("EventTypes")] EventTypes eventTypes,
            Logger<Agent>? logger = null) : base(eventTypes, logger)
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
        var builder = Host.CreateApplicationBuilder();

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
