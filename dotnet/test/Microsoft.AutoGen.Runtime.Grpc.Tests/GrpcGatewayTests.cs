// Copyright (c) Microsoft Corporation. All rights reserved.
// GrpcGatewayTests.cs

using Microsoft.AutoGen.Abstractions;
using Microsoft.AutoGen.Runtime.Grpc.Tests.Helpers.Orleans;
using Microsoft.Extensions.Logging;
using Moq;

namespace Microsoft.AutoGen.Runtime.Grpc.Tests;

[Collection(ClusterCollection.Name)]
public class GrpcGatewayTests
{
    private readonly ClusterFixture _fixture;

    public GrpcGatewayTests(ClusterFixture fixture)
    {
        _fixture = fixture;
    }
    // Test broadcast Event
    [Fact]
    public async Task TestBroadcastEvent()
    {
        var logger = Mock.Of<ILogger<GrpcGateway>>();
        var gateway = new GrpcGateway(_fixture.Cluster.Client, logger);
        var evt = new CloudEvent {
            Type = "TestType",
        };

        // 1. Register Agent
        // 2. Broadcast Event
        // 3.
       
        await gateway.BroadcastEvent(evt);
        //var registry = fixture.Registry;
        //var subscriptions = fixture.Subscriptions;
        //var gateway = new Gateway(registry, subscriptions);
        //var agentId = new AgentId(1, "TestAgent");
        //var worker = new GatewayWorker(agentId, gateway);
        //await registry.AddWorker(worker);
        //var agentType = "TestAgent";
        //var topic = "TestTopic";
        //await subscriptions.Subscribe(agentType, topic);
        //var message = new Message(agentId, topic, new byte[] { 1, 2, 3 });
        //await gateway.BroadcastEvent(message);
        //var receivedMessage = await worker.ReceiveMessage();
        //Assert.Equal(message, receivedMessage);
        //await registry.RemoveWorker(worker);
    }

    // Test StoreAsync
    [Fact]
    public async Task TestStoreAsync()
    {
        var logger = Mock.Of<ILogger<GrpcGateway>>();
        var gateway = new GrpcGateway(_fixture.Cluster.Client, logger);
        var agentState = new AgentState
        {
            AgentId = new AgentId
            {
                Type = "TestType",
                Key = "TestKey",
            },
        };
        await gateway.StoreAsync(agentState);
        //var registry = fixture.Registry;
        //var gateway = new Gateway(registry, subscriptions);
        //var agentId = new AgentId(1, "TestAgent");
        //var worker = new GatewayWorker(agentId, gateway);
        //await registry.AddWorker(worker);
        //var agentState = new AgentState(agentId, new byte[] { 1, 2, 3 });
        //await gateway.StoreAsync(agentState);
        //var receivedAgentState = await worker.ReceiveState();
        //Assert.Equal(agentState, receivedAgentState);
        //await registry.RemoveWorker(worker);
    }

    // Test ReadAsync
    [Fact]
    public async Task TestReadAsync()
    {
        var logger = Mock.Of<ILogger<GrpcGateway>>();
        var gateway = new GrpcGateway(_fixture.Cluster.Client, logger);
        var agentId = new AgentId
        {
            Type = "TestType",
            Key = "TestKey",
        };
        var _ = await gateway.ReadAsync(agentId);
        //var registry = fixture.Registry;
        //var gateway = new Gateway(registry, subscriptions);
        //var agentId = new AgentId(1, "TestAgent");
        //var worker = new GatewayWorker(agentId, gateway);
        //await registry.AddWorker(worker);
        //var agentState = new AgentState(agentId, new byte[] { 1, 2, 3 });
        //await worker.SendState(agentState);
        //var receivedAgentState = await gateway.ReadAsync(agentId);
        //Assert.Equal(agentState, receivedAgentState);
        //await registry.RemoveWorker(worker);
    }

    // Test RegisterAgentTypeAsync
    [Fact]
    public async Task TestRegisterAgentTypeAsync()
    {
        var logger = Mock.Of<ILogger<GrpcGateway>>();
        var gateway = new GrpcGateway(_fixture.Cluster.Client, logger);
        var request = new RegisterAgentTypeRequest
        {
            Type = "TestType",
        };
        var _ = await gateway.RegisterAgentTypeAsync(request);
        //var registry = fixture.Registry;
        //var gateway = new Gateway(registry, subscriptions);
        //var agentType = "TestAgent";
        //var request = new RegisterAgentTypeRequest(agentType);
        //var response = await gateway.RegisterAgentTypeAsync(request);
        //Assert.Equal(agentType, response.AgentType);
    }
}
