// Copyright (c) Microsoft Corporation. All rights reserved.
// GrpcGatewayServiceTests.cs

using FluentAssertions;
using Microsoft.AutoGen.Abstractions;
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
        var callContext = TestServerCallContext.Create();

        using var requestStream = new TestAsyncStreamReader<Message>(callContext);
        using var responseStream = new TestServerStreamWriter<Message>(callContext);

        gateway.WorkersCount.Should().Be(0);
        await service.OpenChannel(requestStream, responseStream, callContext);
        gateway.WorkersCount.Should().Be(1);
    }

    [Fact]
    public async Task Test_Message_Exchange_Through_Gateway()
    {
        var logger = Mock.Of<ILogger<GrpcGateway>>();
        var gateway = new GrpcGateway(_fixture.Cluster.Client, logger);
        var service = new GrpcGatewayService(gateway);
        var callContext = TestServerCallContext.Create();

        using var requestStream = new TestAsyncStreamReader<Message>(callContext);
        using var responseStream = new TestServerStreamWriter<Message>(callContext);

        var assembly = typeof(PBAgent).Assembly;
        var eventTypes = ReflectionHelper.GetAgentsMetadata(assembly);

        await service.OpenChannel(requestStream, responseStream, callContext);
        var responseMessage = await responseStream.ReadNextAsync();

        await service.RegisterAgent(CreateRegistrationRequest(eventTypes, typeof(PBAgent), responseMessage!.Response.RequestId), callContext);
        await service.RegisterAgent(CreateRegistrationRequest(eventTypes, typeof(GMAgent), responseMessage!.Response.RequestId), callContext);

        var inputEvent = new NewMessageReceived { Message = "Hello" }.ToCloudEvent("gh-gh-gh");

        requestStream.AddMessage(new Message { CloudEvent = inputEvent });
        var newMessageReceived = await responseStream.ReadNextAsync();
        newMessageReceived!.CloudEvent.Type.Should().Be(GetFullName(typeof(NewMessageReceived)));

        // Simulate an agent, by publishing a new message in the request stream

        var outputEvent = await responseStream.ReadNextAsync();
        outputEvent!.CloudEvent.Type.Should().Be(GetFullName(typeof(Hello)));

    }

    private RegisterAgentTypeRequest CreateRegistrationRequest(EventTypes eventTypes, Type type, string requestId)
    {
        var registration = new RegisterAgentTypeRequest
        {
            Type = type.Name,
            RequestId = requestId
        };
        registration.Events.AddRange(eventTypes.GetEventsForAgent(type)?.ToList());

        return registration;
    }

    private string GetFullName(Type type)
    {
        return ReflectionHelper.GetMessageDescriptor(type)!.FullName;
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
}
