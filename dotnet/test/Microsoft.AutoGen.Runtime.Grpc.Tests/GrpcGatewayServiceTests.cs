// Copyright (c) Microsoft Corporation. All rights reserved.
// GrpcGatewayServiceTests.cs

using FluentAssertions;
using Microsoft.AutoGen.Contracts;
using Microsoft.AutoGen.Core;
using Microsoft.AutoGen.Runtime.Grpc.Tests.Helpers.Grpc;
using Microsoft.AutoGen.Runtime.Grpc.Tests.Helpers.Orleans;
using Microsoft.Extensions.Logging;
using Moq;
using NewMessageReceived = Tests.Events.NewMessageReceived;

namespace Microsoft.AutoGen.Runtime.Grpc.Tests;
[Collection(ClusterCollection.Name)]
[Trait("Category", "UnitV2")]
public class GrpcGatewayServiceTests
{
    private readonly ClusterFixture _fixture;

    public GrpcGatewayServiceTests(ClusterFixture fixture)
    {
        _fixture = fixture;
    }
    [Fact]
    public async Task Test_OpenChannel()
    {
        var logger = Mock.Of<ILogger<GrpcGateway>>();
        var gateway = new GrpcGateway(_fixture.Cluster.Client, logger);
        var service = new GrpcGatewayService(gateway);
        var client = new TestGrpcClient();

        gateway._workers.Count.Should().Be(0);
        var task = OpenChannel(service, client);
        gateway._workers.Count.Should().Be(1);
        client.Dispose();
        await task;
    }

    [Fact]
    public async Task Test_Message_Exchange_Through_Gateway()
    {
        var logger = Mock.Of<ILogger<GrpcGateway>>();
        var gateway = new GrpcGateway(_fixture.Cluster.Client, logger);
        var service = new GrpcGatewayService(gateway);
        var client = new TestGrpcClient();
        var task = OpenChannel(service: service, client);
        await service.RegisterAgent(await CreateRegistrationRequest(service, typeof(PBAgent), client.CallContext.Peer), client.CallContext);
        await service.RegisterAgent(await CreateRegistrationRequest(service, typeof(GMAgent), client.CallContext.Peer), client.CallContext);

        var inputEvent = new NewMessageReceived { Message = $"Start-{client.CallContext.Peer}" }.ToCloudEvent("gh-gh-gh", "gh-gh-gh");

        client.AddMessage(new Message { CloudEvent = inputEvent });
        var newMessageReceived = await client.ReadNext();
        newMessageReceived!.CloudEvent.Type.Should().Be(GetFullName(typeof(NewMessageReceived)));
        newMessageReceived.CloudEvent.Source.Should().Be("gh-gh-gh");
        var secondMessage = await client.ReadNext();
        secondMessage!.CloudEvent.Type.Should().Be(GetFullName(typeof(NewMessageReceived)));

        // Simulate an agent, by publishing a new message in the request stream
        var helloEvent = new Hello { Message = $"Hello test-{client.CallContext.Peer}" }.ToCloudEvent("gh-gh-gh", "gh-gh-gh");
        client.AddMessage(new Message { CloudEvent = helloEvent });
        var helloMessageReceived = await client.ReadNext();
        helloMessageReceived!.CloudEvent.Type.Should().Be(GetFullName(typeof(Hello)));
        helloMessageReceived.CloudEvent.Source.Should().Be("gh-gh-gh");
        client.Dispose();
        await task;
    }

    [Fact]
    public async Task Test_RegisterAgent_Should_Succeed()
    {
        var logger = Mock.Of<ILogger<GrpcGateway>>();
        var gateway = new GrpcGateway(_fixture.Cluster.Client, logger);
        var service = new GrpcGatewayService(gateway);
        var client = new TestGrpcClient();
        var task = OpenChannel(service: service, client);
        var response = await service.RegisterAgent(await CreateRegistrationRequest(service, typeof(PBAgent), client.CallContext.Peer), client.CallContext);
        response.Success.Should().BeTrue();
        client.Dispose();
        await task;
    }

    [Fact]
    public async Task Test_RegisterAgent_Should_Fail_For_Wrong_ConnectionId()
    {
        var logger = Mock.Of<ILogger<GrpcGateway>>();
        var gateway = new GrpcGateway(_fixture.Cluster.Client, logger);
        var service = new GrpcGatewayService(gateway);
        var client = new TestGrpcClient();
        var response = await service.RegisterAgent(await CreateRegistrationRequest(service, typeof(PBAgent), "faulty_connection_id"), client.CallContext);
        response.Success.Should().BeFalse();
        client.Dispose();
    }

    [Fact]
    public async Task Test_SaveState()
    {
        var logger = Mock.Of<ILogger<GrpcGateway>>();
        var gateway = new GrpcGateway(_fixture.Cluster.Client, logger);
        var service = new GrpcGatewayService(gateway);
        var callContext = TestServerCallContext.Create();
        var response = await service.SaveState(new AgentState { AgentId = new AgentId { Key = "Test", Type = "test" } }, callContext);
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

    private async Task<RegisterAgentTypeRequest> CreateRegistrationRequest(GrpcGatewayService service, Type type, string requestId)
    {
        var registration = new RegisterAgentTypeRequest
        {
            Type = type.Name,
            RequestId = requestId
        };
        var assembly = type.Assembly;
        var eventTypes = ReflectionHelper.GetAgentsMetadata(assembly);
        var events = eventTypes.GetEventsForAgent(type)?.ToList();
        var topics = eventTypes.GetTopicsForAgent(type)?.ToList();
        if (events is not null && topics is not null) { events.AddRange(topics); }
        var client = new TestGrpcClient();

        if (events != null)
        {
            foreach (var e in events)
            {
                var subscriptionRequest = new Message
                {
                    AddSubscriptionRequest = new AddSubscriptionRequest
                    {
                        RequestId = Guid.NewGuid().ToString(),
                        Subscription = new Subscription
                        {
                            TypeSubscription = new TypeSubscription
                            {
                                AgentType = type.Name,
                                TopicType = type.Name + "." + e
                            }
                        }
                    }
                };
                await service.AddSubscription(subscriptionRequest.AddSubscriptionRequest, client.CallContext);
            }
        }
        var topicTypes = type.GetCustomAttributes(typeof(TopicSubscriptionAttribute), true).Cast<TopicSubscriptionAttribute>().Select(t => t.Topic).ToList();
        if (topicTypes != null)
        {
            foreach (var topicType in topicTypes)
            {
                var subscriptionRequest = new Message
                {
                    AddSubscriptionRequest = new AddSubscriptionRequest
                    {
                        RequestId = Guid.NewGuid().ToString(),
                        Subscription = new Subscription
                        {
                            TypeSubscription = new TypeSubscription
                            {
                                AgentType = type.Name,
                                TopicType = topicType
                            }
                        }
                    }
                };
                await service.AddSubscription(subscriptionRequest.AddSubscriptionRequest, client.CallContext);
            }
        }
        return registration;
    }

    private Task OpenChannel(GrpcGatewayService service, TestGrpcClient client)
    {
        return service.OpenChannel(client.RequestStream, client.ResponseStream, client.CallContext);
    }
    private string GetFullName(Type type)
    {
        return ReflectionHelper.GetMessageDescriptor(type)!.FullName;
    }
}
