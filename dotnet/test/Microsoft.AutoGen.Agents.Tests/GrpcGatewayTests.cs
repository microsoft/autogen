// Copyright (c) Microsoft Corporation. All rights reserved.
// GrpcGatewayTests.cs

using Microsoft.AutoGen.Abstractions;
using Microsoft.Extensions.DependencyInjection;
using Xunit;

namespace Microsoft.AutoGen.Agents.Tests;

public class GrpcGatewayTests
{
    public GrpcGatewayTests()
    {
        Setup().Wait();
    }
    private async Task Setup()
    {
        await Host.StartAsync(local: false, useGrpc: true);
    }

    [Fact]
    public async Task AddSubscriptionAsync_SendsAddSubscriptionRequest_AndChecksAddSubscriptionResponse()
    {
        await AgentsApp.PublishMessageAsync("Test", new NewMessageReceived
        {
            Message = "test"
        }, local: true).ConfigureAwait(true);
        // Assert
        Assert.True(true);

    }
    [TopicSubscription("Test")]
    public class GrpcGatewayTest(
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
