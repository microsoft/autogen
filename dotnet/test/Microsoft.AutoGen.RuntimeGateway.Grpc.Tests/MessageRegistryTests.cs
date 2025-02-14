// Copyright (c) Microsoft Corporation. All rights reserved.
// MessageRegistryTests.cs

using Microsoft.AutoGen.Contracts;
using Microsoft.AutoGen.RuntimeGateway.Grpc.Abstractions;
using Microsoft.AutoGen.RuntimeGateway.Grpc.Tests.Helpers.Orleans;
using Orleans.TestingHost;

namespace Microsoft.AutoGen.RuntimeGateway.Grpc.Tests;
public class MessageRegistryTests : IClassFixture<ClusterFixture>
{
    private readonly TestCluster _cluster;

    public MessageRegistryTests(ClusterFixture fixture)
    {
        _cluster = fixture.Cluster;
    }

    [Fact]
    public async Task Write_and_Remove_Messages()
    {
        // Arrange
        var grain = _cluster.GrainFactory.GetGrain<IMessageRegistryGrain>(0);
        var topic = Guid.NewGuid().ToString(); // Random topic
        var message = new CloudEvent { Id = Guid.NewGuid().ToString(), Source = "test-source", Type = "test-type" };

        // Act
        await grain.WriteMessageAsync(topic, message);

        // Assert
        // attempt to remove the topic from the queue
        var removedMessages = await grain.RemoveMessagesAsync(topic);
        // attempt to compare the message with the removed message
        Assert.Single(removedMessages);
        Assert.Equal(message.Id, removedMessages[0].Id);
        // ensure the queue is empty
        removedMessages = await grain.RemoveMessagesAsync(topic);
        Assert.Empty(removedMessages);
    }
}
