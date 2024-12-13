// Copyright (c) Microsoft Corporation. All rights reserved.
// InMemoryAgentTests.cs

using FluentAssertions;
using Google.Protobuf.Reflection;
using Microsoft.AutoGen.Contracts;
using Microsoft.AutoGen.Core.Tests.Helpers;
using Microsoft.Extensions.DependencyInjection;
using Tests.Events;
using Xunit;

namespace Microsoft.AutoGen.Core.Tests;

[Collection(CoreFixtureCollection.Name)]
public partial class InMemoryAgentTests(InMemoryAgentRuntimeFixture fixture)
{
    private readonly InMemoryAgentRuntimeFixture _fixture = fixture;

    [Fact]
    public async Task ItInvokeRightHandlerTestAsync()
    {
        var context = _fixture.CreateContext(new AgentId { Type = "", Key = "" });
        var agent = new TestAgent(new AgentsMetadata(TypeRegistry.Empty, [], [], []));
        Agent.Initialize(context, agent);
        await agent.Handle(new TextMessage { Source = "test", Message = "Wow" }, CancellationToken.None);

        TestAgent.ReceivedMessages.Count.Should().Be(1);
        TestAgent.ReceivedMessages["test"].Should().Be("Wow");
    }

    [Fact]
    public async Task Agent_Handles_Event()
    {
        var agentId = new AgentId { Type = "test", Key = "1" };
        var context = _fixture.CreateContext(agentId);
        var client = _fixture.AppHost.Services.GetRequiredService<Client>();
        Agent.Initialize(context, client);
        var evt = new TextMessage { Message = $"wow{agentId.Key}", Source = nameof(Agent_Handles_Event) };
        await client.PublishEventAsync(evt, agentId.Key, "default", CancellationToken.None);

        // wait for 10 seconds
        var cts = new CancellationTokenSource(TimeSpan.FromSeconds(10));
        while (!TestAgent.ReceivedMessages.ContainsKey(nameof(Agent_Handles_Event)) && !cts.Token.IsCancellationRequested)
        {
            await Task.Delay(100);
        }

        TestAgent.ReceivedMessages[nameof(Agent_Handles_Event)].Should().NotBeNull();
        TestAgent.ReceivedMessages[nameof(Agent_Handles_Event)].Should().Be($"wow{agentId.Key}");
    }
}
