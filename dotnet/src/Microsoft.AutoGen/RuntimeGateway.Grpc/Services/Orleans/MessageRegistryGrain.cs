// Copyright (c) Microsoft Corporation. All rights reserved.
// MessageRegistryGrain.cs

using Microsoft.AutoGen.Contracts;
using Microsoft.AutoGen.RuntimeGateway.Grpc.Abstractions;
using Microsoft.Extensions.Logging;

namespace Microsoft.AutoGen.RuntimeGateway.Grpc;

internal sealed class MessageRegistryGrain : Grain, IMessageRegistryGrain
{
    public enum QueueType
    {
        DeadLetterQueue,
        EventBuffer
    }

    /// <summary>
    /// The time to wait before removing a message from the event buffer.
    /// in milliseconds
    /// </summary>
    private const int _bufferTime = 5000;

    /// <summary>
    /// maximum size of a message we will write to the state store in bytes
    /// </summary>
    /// <remarks>set this to HALF your intended limit as protobuf strings are UTF8 but .NET UTF16</remarks>
    private const int _maxMessageSize = 1024 * 1024 * 99; // 99MB

    /// <summary>
    /// maximum size of a each queue
    /// </summary>
    /// <remarks>set this to HALF your intended limit as protobuf strings are UTF8 but .NET UTF16</remarks>
    private const int _maxQueueSize = 1024 * 1024 * 256; // 256MB

    private readonly MessageRegistryQueue _dlqQueue;
    private readonly MessageRegistryQueue _ebQueue;

    public MessageRegistryGrain(
        [PersistentState("state", "PubSubStore")] IPersistentState<MessageRegistryState> state,
        ILogger<MessageRegistryGrain> logger)
    {
        _dlqQueue = new MessageRegistryQueue(
            QueueType.DeadLetterQueue,
            state,
            new StateManager(state),
            logger,
            _maxMessageSize,
            _maxQueueSize);

        _ebQueue = new MessageRegistryQueue(
            QueueType.EventBuffer,
            state,
            new StateManager(state),
            logger,
            _maxMessageSize,
            _maxQueueSize);
    }

    // <inheritdoc />
    public async Task AddMessageToDeadLetterQueueAsync(string topic, CloudEvent message)
    {
        await _dlqQueue.AddMessageAsync(topic, message);
    }

    ///<inheritdoc />
    public async Task AddMessageToEventBufferAsync(string topic, CloudEvent message)
    {
        await _ebQueue.AddMessageAsync(topic, message);
        _ebQueue.RemoveMessageAfterDelayAsync(topic, message, _bufferTime).Ignore();
    }

    // <inheritdoc />
    public async Task<List<CloudEvent>> RemoveMessagesAsync(string topic)
    {
        var removedDeadLetter = await _dlqQueue.RemoveMessagesAsync(topic);
        var removedBuffer = await _ebQueue.RemoveMessagesAsync(topic);
        return removedDeadLetter.Concat(removedBuffer).ToList();
    }
}
