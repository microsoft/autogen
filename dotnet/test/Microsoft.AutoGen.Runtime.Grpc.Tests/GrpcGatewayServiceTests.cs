// Copyright (c) Microsoft Corporation. All rights reserved.
// GrpcGatewayServiceTests.cs

using FluentAssertions;
using Microsoft.AutoGen.Contracts;
using Microsoft.AutoGen.Core;
using Microsoft.AutoGen.Runtime.Grpc.Tests.Helpers.Grpc;
using Microsoft.AutoGen.Runtime.Grpc.Tests.Helpers.Orleans;
using Microsoft.Extensions.Logging;
using Moq;
using Tests.Events;

namespace Microsoft.AutoGen.Runtime.Grpc.Tests;
[Collection(ClusterCollection.Name)]
public class GrpcGatewayServiceTests
{
    private readonly ClusterFixture _fixture;

    public GrpcGatewayServiceTests(ClusterFixture fixture)
    {
        _fixture = fixture;
    }
    // Test broadcast Event
    [Fact]
    public async Task Test_OpenChannel()
    {
        var logger = Mock.Of<ILogger<GrpcGateway>>();
        var gateway = new GrpcGateway(_fixture.Cluster.Client, logger);
        var service = new GrpcGatewayService(gateway);
        using var client = new TestGrpcClient();
        
        gateway.WorkersCount.Should().Be(0);
        await service.OpenChannel(client.RequestStream, client.ResponseStream, client.CallContext);
        gateway.WorkersCount.Should().Be(1);
    }

    [Fact]
    public async Task Test_Message_Exchange_Through_Gateway()
    {
        var logger = Mock.Of<ILogger<GrpcGateway>>();
        var gateway = new GrpcGateway(_fixture.Cluster.Client, logger);
        var service = new GrpcGatewayService(gateway);
        using var client = new TestGrpcClient();

        var assembly = typeof(PBAgent).Assembly;
        var eventTypes = ReflectionHelper.GetAgentsMetadata(assembly);

        await service.OpenChannel(client.RequestStream, client.ResponseStream, client.CallContext);

        await service.RegisterAgent(CreateRegistrationRequest(eventTypes, typeof(PBAgent), client.CallContext.Peer), client.CallContext);
        await service.RegisterAgent(CreateRegistrationRequest(eventTypes, typeof(GMAgent), client.CallContext.Peer), client.CallContext);

        var inputEvent = new NewMessageReceived { Message = $"Start-{client.CallContext.Peer}" }.ToCloudEvent("gh-gh-gh", "gh-gh-gh");

        client.AddMessage(new Message { CloudEvent = inputEvent });
        var newMessageReceived = await client.ReadNext();
        newMessageReceived!.CloudEvent.Type.Should().Be(GetFullName(typeof(NewMessageReceived)));
        newMessageReceived.CloudEvent.Source.Should().Be("gh-gh-gh");

        // Simulate an agent, by publishing a new message in the request stream
        var helloEvent = new Hello { Message = $"Hello test-{client.CallContext.Peer}" }.ToCloudEvent("gh-gh-gh", "gh-gh-gh");
        client.AddMessage(new Message { CloudEvent = helloEvent });

        var helloMessageReceived = await client.ReadNext();
        helloMessageReceived!.CloudEvent.Type.Should().Be(GetFullName(typeof(Hello)));
        helloMessageReceived.CloudEvent.Source.Should().Be("gh-gh-gh");
    }

    [Fact]
    public async Task Test_Message_Goes_To_Right_Worker()
    {
        var logger = Mock.Of<ILogger<GrpcGateway>>();
        var gateway = new GrpcGateway(_fixture.Cluster.Client, logger);
        var service = new GrpcGatewayService(gateway);
        using var client = new TestGrpcClient();

        var assembly = typeof(PBAgent).Assembly;
        var eventTypes = ReflectionHelper.GetAgentsMetadata(assembly);

        await service.OpenChannel(client.RequestStream, client.ResponseStream, client.CallContext);

        await service.RegisterAgent(CreateRegistrationRequest(eventTypes, typeof(PBAgent), client.CallContext.Peer), client.CallContext);
        await service.RegisterAgent(CreateRegistrationRequest(eventTypes, typeof(GMAgent), client.CallContext.Peer), client.CallContext);

    }

    [Fact]
    public async Task Test_RegisterAgent_Should_Succeed()
    {
        var logger = Mock.Of<ILogger<GrpcGateway>>();
        var gateway = new GrpcGateway(_fixture.Cluster.Client, logger);
        var service = new GrpcGatewayService(gateway);
        using var client = new TestGrpcClient();

        var assembly = typeof(PBAgent).Assembly;
        var eventTypes = ReflectionHelper.GetAgentsMetadata(assembly);

        await service.OpenChannel(client.RequestStream, client.ResponseStream, client.CallContext);

        var response = await service.RegisterAgent(CreateRegistrationRequest(eventTypes, typeof(PBAgent), client.CallContext.Peer), client.CallContext);
        response.Success.Should().BeTrue();
    }

    [Fact]
    public async Task Test_RegisterAgent_Should_Fail_For_Wrong_ConnectionId()
    {
        var logger = Mock.Of<ILogger<GrpcGateway>>();
        var gateway = new GrpcGateway(_fixture.Cluster.Client, logger);
        var service = new GrpcGatewayService(gateway);
        using var client = new TestGrpcClient();

        var assembly = typeof(PBAgent).Assembly;
        var eventTypes = ReflectionHelper.GetAgentsMetadata(assembly);

        var response = await service.RegisterAgent(CreateRegistrationRequest(eventTypes, typeof(PBAgent), "faulty_connection_id"), client.CallContext);
        response.Success.Should().BeFalse();
    }

    [Fact]
    public async Task Test_SaveState()
    {
        var logger = Mock.Of<ILogger<GrpcGateway>>();
        var gateway = new GrpcGateway(_fixture.Cluster.Client, logger);
        var service = new GrpcGatewayService(gateway);
        var callContext = TestServerCallContext.Create();

        var response = await service.SaveState(new AgentState { AgentId = new AgentId { Key = "", Type = "" } }, callContext);

        response.Should().NotBeNull();
    }

    [Fact]
    public async Task Test_GetState()
    {
        var logger = Mock.Of<ILogger<GrpcGateway>>();
        var gateway = new GrpcGateway(_fixture.Cluster.Client, logger);
        var service = new GrpcGatewayService(gateway);
        var callContext = TestServerCallContext.Create();

        var response = await service.GetState(new AgentId { Key = "", Type = "" }, callContext);

        response.Should().NotBeNull();
    }

    private RegisterAgentTypeRequest CreateRegistrationRequest(AgentsMetadata eventTypes, Type type, string requestId)
    {
        var registration = new RegisterAgentTypeRequest
        {
            Type = type.Name,
            RequestId = requestId
        };
        registration.Events.AddRange(eventTypes.GetEventsForAgent(type)?.ToList());
        registration.Topics.AddRange(eventTypes.GetTopicsForAgent(type)?.ToList());

        return registration;
    }

    private string GetFullName(Type type)
    {
        return ReflectionHelper.GetMessageDescriptor(type)!.FullName;
    }
}
