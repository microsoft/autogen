// Copyright (c) Microsoft Corporation. All rights reserved.
// GrpcGatewayServiceTests.cs

using FluentAssertions;
using Microsoft.AutoGen.Contracts;
using Microsoft.AutoGen.Core;
using Microsoft.AutoGen.Protobuf;
using Microsoft.AutoGen.RuntimeGateway.Grpc.Tests.Helpers.Grpc;
using Microsoft.AutoGen.RuntimeGateway.Grpc.Tests.Helpers.Orleans;
using Microsoft.Extensions.Logging;
using Moq;
using NewMessageReceived = Tests.Events.NewMessageReceived;

namespace Microsoft.AutoGen.RuntimeGateway.Grpc.Tests;
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
        await service.RegisterAgent(await CreateRegistrationRequest(service, typeof(PBAgent)), client.CallContext);
        await service.RegisterAgent(await CreateRegistrationRequest(service, typeof(GMAgent)), client.CallContext);

        //var inputEvent = new NewMessageReceived { Message = $"Start-{client.CallContext.Peer}" }.ToCloudEvent("gh-gh-gh", "gh-gh-gh");
        var newMessage = new NewMessageReceived { Message = $"Start-{client.CallContext.Peer}" };
        var eventType = GetFullName(typeof(NewMessageReceived));
        var inputEvent = CloudEventExtensions.CreateCloudEvent(
            Google.Protobuf.WellKnownTypes.Any.Pack(newMessage),
            new TopicId(eventType, "gh-gh-gh"),
            eventType,
            null,
            Guid.NewGuid().ToString());

        client.AddMessage(new Message { CloudEvent = inputEvent });
        var newMessageReceived = await client.ReadNext();
        newMessageReceived!.CloudEvent.Type.Should().Be(GetFullName(typeof(NewMessageReceived)));
        newMessageReceived.CloudEvent.Source.Should().Be("gh-gh-gh");
        var secondMessage = await client.ReadNext();
        secondMessage!.CloudEvent.Type.Should().Be(GetFullName(typeof(NewMessageReceived)));

        // Simulate an agent, by publishing a new message in the request stream
        //var helloEvent = new Hello { Message = $"Hello test-{client.CallContext.Peer}" }.ToCloudEvent("gh-gh-gh", "gh-gh-gh");
        var hello = new Hello { Message = $"Hello test-{client.CallContext.Peer}" };
        var eventTypeHello = GetFullName(typeof(Hello));
        var helloEvent = CloudEventExtensions.CreateCloudEvent(
            Google.Protobuf.WellKnownTypes.Any.Pack(message: hello),
            new TopicId(eventTypeHello, "gh-gh-gh"),
            eventTypeHello,
            null,
            Guid.NewGuid().ToString()
        );
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
        var response = await service.RegisterAgent(await CreateRegistrationRequest(service, typeof(PBAgent)), client.CallContext);
        response.GetType().Should().Be(typeof(RegisterAgentTypeResponse));
        client.Dispose();
        await task;
    }

    private async Task<RegisterAgentTypeRequest> CreateRegistrationRequest(GrpcGatewayService service, Type type)
    {
        var registration = new RegisterAgentTypeRequest
        {
            Type = type.Name,
        };
        var assembly = type.Assembly;
        var eventTypes = ReflectionHelper.GetAgentsMetadata(assembly);
        var events = eventTypes.GetEventsForAgent(type)?.ToList();
        var topics = eventTypes.GetTopicsForAgent(type)?.ToList();
        var topicsPrefix = eventTypes.GetTopicsPrefixForAgent(type)?.ToList();
        if (events is not null && topics is not null) { events.AddRange(topics); }
        var client = new TestGrpcClient();

        if (events != null)
        {
            foreach (var e in events)
            {
                var subscriptionRequest = new AddSubscriptionRequest
                {
                    Subscription = new Subscription
                    {
                        Id = Guid.NewGuid().ToString(),
                        TypeSubscription = new Protobuf.TypeSubscription
                        {
                            AgentType = type.Name,
                            TopicType = type.Name + "." + e
                        }
                    }

                };
                await service.AddSubscription(subscriptionRequest, client.CallContext);
            }
        }
        var topicTypes = type.GetCustomAttributes(typeof(TypeSubscriptionAttribute), true).Cast<TypeSubscriptionAttribute>().Select(t => t.Topic).ToList();
        if (topicTypes != null)
        {
            foreach (var topicType in topicTypes)
            {
                var subscriptionRequest = new AddSubscriptionRequest
                {
                    Subscription = new Subscription
                    {
                        Id = Guid.NewGuid().ToString(),
                        TypeSubscription = new Protobuf.TypeSubscription
                        {
                            AgentType = type.Name,
                            TopicType = topicType
                        }
                    }

                };
                await service.AddSubscription(subscriptionRequest, client.CallContext);
            }
        }
        var topicPrefixTypes = type.GetCustomAttributes(typeof(TypePrefixSubscriptionAttribute), true).Cast<TypePrefixSubscriptionAttribute>().Select(t => t.Topic).ToList();
        if (topicPrefixTypes != null)
        {
            foreach (var topicType in topicPrefixTypes)
            {
                var subscriptionRequest = new AddSubscriptionRequest
                {
                    Subscription = new Subscription
                    {
                        Id = Guid.NewGuid().ToString(),
                        TypePrefixSubscription = new Protobuf.TypePrefixSubscription
                        {
                            AgentType = type.Name,
                            TopicTypePrefix = topicType
                        }
                    }

                };
                await service.AddSubscription(subscriptionRequest, client.CallContext);
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
    /// duplicate code here because I could not get InternalsVisibleTo to work
    internal static class Constants
    {
        public const string DATA_CONTENT_TYPE_PROTOBUF_VALUE = "application/x-protobuf";
        public const string DATA_CONTENT_TYPE_JSON_VALUE = "application/json";
        public const string DATA_CONTENT_TYPE_TEXT_VALUE = "text/plain";

        public const string DATA_CONTENT_TYPE_ATTR = "datacontenttype";
        public const string DATA_SCHEMA_ATTR = "dataschema";
        public const string AGENT_SENDER_TYPE_ATTR = "agagentsendertype";
        public const string AGENT_SENDER_KEY_ATTR = "agagentsenderkey";

        public const string MESSAGE_KIND_ATTR = "agmsgkind";
        public const string MESSAGE_KIND_VALUE_PUBLISH = "publish";
        public const string MESSAGE_KIND_VALUE_RPC_REQUEST = "rpc_request";
        public const string MESSAGE_KIND_VALUE_RPC_RESPONSE = "rpc_response";
    }
    internal static class CloudEventExtensions
    {
        // Convert an ISubscrptionDefinition to a Protobuf Subscription
        internal static CloudEvent CreateCloudEvent(Google.Protobuf.WellKnownTypes.Any payload, TopicId topic, string dataType, Contracts.AgentId? sender, string messageId)
        {
            var attributes = new Dictionary<string, CloudEvent.Types.CloudEventAttributeValue>
            {
                {
                    Constants.DATA_CONTENT_TYPE_ATTR, new CloudEvent.Types.CloudEventAttributeValue { CeString = Constants.DATA_CONTENT_TYPE_PROTOBUF_VALUE }
                },
                {
                    Constants.DATA_SCHEMA_ATTR, new CloudEvent.Types.CloudEventAttributeValue { CeString = dataType }
                },
                {
                    Constants.MESSAGE_KIND_ATTR, new CloudEvent.Types.CloudEventAttributeValue { CeString = Constants.MESSAGE_KIND_VALUE_PUBLISH }
                }
            };

            if (sender != null)
            {
                var senderNonNull = (Contracts.AgentId)sender;
                attributes.Add(Constants.AGENT_SENDER_TYPE_ATTR, new CloudEvent.Types.CloudEventAttributeValue { CeString = senderNonNull.Type });
                attributes.Add(Constants.AGENT_SENDER_KEY_ATTR, new CloudEvent.Types.CloudEventAttributeValue { CeString = senderNonNull.Key });
            }

            return new CloudEvent
            {
                ProtoData = payload,
                Type = topic.Type,
                Source = topic.Source,
                Id = messageId,
                Attributes = { attributes }
            };

        }
    }
}
