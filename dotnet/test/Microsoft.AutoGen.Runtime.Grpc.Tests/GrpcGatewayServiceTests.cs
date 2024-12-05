// Copyright (c) Microsoft Corporation. All rights reserved.
// GrpcGatewayServiceTests.cs

using FluentAssertions;
using Microsoft.AutoGen.Abstractions;
using Microsoft.AutoGen.Runtime.Grpc.Tests.Helpers.Grpc;
using Microsoft.AutoGen.Runtime.Grpc.Tests.Helpers.Orleans;
using Microsoft.Extensions.Logging;
using Moq;

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
        var requestStream = new TestAsyncStreamReader<Message>(callContext);
        var responseStream = new TestServerStreamWriter<Message>(callContext);

        await service.OpenChannel(requestStream, responseStream, callContext);

        requestStream.AddMessage(new Message {  });

        requestStream.Complete();

        responseStream.Complete();

        var responseMessage = await responseStream.ReadNextAsync();
        responseMessage.Should().NotBeNull();
    }

    [Fact]
    public async Task Test_SaveState()
    {
        var logger = Mock.Of<ILogger<GrpcGateway>>();
        var gateway = new GrpcGateway(_fixture.Cluster.Client, logger);
        var service = new GrpcGatewayService(gateway);
        var callContext = TestServerCallContext.Create();

        var response = await service.SaveState(new AgentState { }, callContext);

        response.Should().NotBeNull();
    }

    [Fact]
    public async Task Test_GetState()
    {
        var logger = Mock.Of<ILogger<GrpcGateway>>();
        var gateway = new GrpcGateway(_fixture.Cluster.Client, logger);
        var service = new GrpcGatewayService(gateway);
        var callContext = TestServerCallContext.Create();

        var response = await service.GetState(new AgentId { }, callContext);

        response.Should().NotBeNull();
    }
}
