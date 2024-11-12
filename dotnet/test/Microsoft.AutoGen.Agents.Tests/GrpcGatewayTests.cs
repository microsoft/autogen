// Copyright (c) Microsoft Corporation. All rights reserved.
// GrpcGatewayTests.cs

using Grpc.Core;
using Microsoft.AutoGen.Abstractions;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Moq;
using Xunit;

namespace Microsoft.AutoGen.Agents.Tests;

public class GrpcGatewayTests
{
    public GrpcGatewayTests()
    {
        Setup();
    }
    private async ValueTask Setup()
    {
        await Host.StartAsync(local: false, useGrpc: true).ConfigureAwait(true);
        await AgentsApp.PublishMessageAsync("Test", new NewMessageReceived
        {
            Message = "test"
        }, local: true).ConfigureAwait(true);
    }

    [Fact]
    public async Task AddSubscriptionAsync_SendsAddSubscriptionRequest_AndChecksAddSubscriptionResponse()
    {


        // Assert
        responseStream.Verify(stream => stream.WriteAsync(It.Is<Message>(msg =>
            msg.AddSubscriptionResponse.RequestId == request.RequestId &&
            msg.AddSubscriptionResponse.Error == "" &&
            msg.AddSubscriptionResponse.Success == true), default), Times.Once);
    }
    [TopicSubscription("Test")]
    public class TestAgent(
              IAgentRuntime context,
            [FromKeyedServices("EventTypes")] EventTypes typeRegistry) : AgentBase(
              context,
              typeRegistry), IHandle<NewMessageReceived>
    {
        public async Task Handle(NewMessageReceived item)
        {
            // update our subscription requests
            await SendSubscriptionRequestAsync().ConfigureAwait(false);
        }
        private async ValueTask SendSubscriptionRequestAsync(CancellationToken cancellationToken = default)
        {
            Message request = new()
            {
                AddSubscriptionRequest = new()
                {
                    RequestId = "test-request-id",
                    Subscription = new Subscription
                    {
                        TypeSubscription = new TypeSubscription
                        {
                            TopicType = "test-topic",
                            AgentType = "test-agent-type"
                        }
                    }
                }
            };
            await Context.SendMessageAsync(request, cancellationToken).ConfigureAwait(false);
        }
    }
}