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
        await grain.AddMessageToDeadLetterQueueAsync(topic, message);

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
    /// <summary>
    /// Test that messages are removed from the event buffer after the buffer time
    /// </summary>
    [Fact]
    public async Task Write_and_Remove_Messages_BufferTime()
    {
        // Arrange
        var grain = _cluster.GrainFactory.GetGrain<IMessageRegistryGrain>(0);
        var topic = Guid.NewGuid().ToString(); // Random topic
        var message = new CloudEvent { Id = Guid.NewGuid().ToString(), Source = "test-source", Type = "test-type" };

        // Act
        await grain.AddMessageToEventBufferAsync(topic, message);
        // wait 5 seconds
        await Task.Delay(5000);
        // attempt to remove the topic from the queue
        var removedMessages = await grain.RemoveMessagesAsync(topic);
        Assert.Empty(removedMessages);
    }

    /// <summary>
    /// Test that messages are still in the event buffer after 1 second
    /// </summary>
    [Fact]
    public async Task Write_and_Remove_Messages_BufferTime_StillInBuffer()
    {
        // Arrange
        var grain = _cluster.GrainFactory.GetGrain<IMessageRegistryGrain>(0);
        var topic = Guid.NewGuid().ToString(); // Random topic
        var message = new CloudEvent { Id = Guid.NewGuid().ToString(), Source = "test-source", Type = "test-type" };

        // Act
        await grain.AddMessageToEventBufferAsync(topic, message);
        // wait 1 second
        await Task.Delay(1000);
        // attempt to remove the topic from the queue
        var removedMessages = await grain.RemoveMessagesAsync(topic);
        Assert.Single(removedMessages);
    }

    /// <summary>
    /// Test that messages which exceed the mas message size are not written to the event buffer
    /// </summary>
    [Fact]
    public async Task Do_No_Buffer_If_Messages_Exceed_MaxMessageSize()
    {
        // Arrange
        var grain = _cluster.GrainFactory.GetGrain<IMessageRegistryGrain>(0);
        var topic = Guid.NewGuid().ToString(); // Random topic
        var maxMessageSize = 1024 * 1024 * 99; // 99MB
        var message = new CloudEvent { Id = Guid.NewGuid().ToString(), Source = "test-source", Type = "test-type" };
        
        // Act        
        await grain.AddMessageToEventBufferAsync(topic, message); // small message
        message.BinaryData = Google.Protobuf.ByteString.CopyFrom(new byte[maxMessageSize + 1]);
        await grain.AddMessageToEventBufferAsync(topic, message); // over the limit
        // attempt to remove the topic from the queue
        var removedMessages = await grain.RemoveMessagesAsync(topic);
        Assert.Single(removedMessages); // only the small message should be in the buffer
    }

    /// <summary>
    /// Test that the queue cannot grow past the max queue size
    /// </summary>
    [Fact]
    public async Task Do_No_Buffer_If_Queue_Exceeds_MaxQueueSize()
    {
        // Arrange
        var grain = _cluster.GrainFactory.GetGrain<IMessageRegistryGrain>(0);
        var topic = Guid.NewGuid().ToString(); // Random topic
        var bigMessage = 1024 * 1024 * 99; // 99MB
        var message = new CloudEvent { Id = Guid.NewGuid().ToString(), Source = "test-source", Type = "test-type" };
        
        // Act
        for (int i = 0; i < 11; i++)
        {
            message.BinaryData = Google.Protobuf.ByteString.CopyFrom(new byte[bigMessage]);
            message.Source = i.ToString();
            await grain.AddMessageToEventBufferAsync(topic, message);
        }
        // attempt to remove the topic from the queue
        var removedMessages = await grain.RemoveMessagesAsync(topic);
        Assert.Equal(10, removedMessages.Count); // only 10 messages should be in the buffer

    }
}
