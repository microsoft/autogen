// Copyright (c) Microsoft Corporation. All rights reserved.
// MessageRegistryGrain.cs

using Microsoft.AutoGen.Contracts;
using Microsoft.AutoGen.RuntimeGateway.Grpc.Abstractions;
using Microsoft.Extensions.Logging;

namespace Microsoft.AutoGen.RuntimeGateway.Grpc;

internal sealed class MessageRegistryGrain(
    [PersistentState("state", "PubSubStore")] IPersistentState<MessageRegistryState> state,
    ILogger<MessageRegistryGrain> logger
) : Grain, IMessageRegistryGrain
{
    private const string dlq = "Dead Letter Queue";
    private const string eb = "Event Buffer";

    // <summary>
    // Helper class for managing state writes.
    // </summary>
    private readonly StateManager _stateManager = new(state);

    // <summary>
    // The number of times to retry writing the state before giving up.
    // </summary>
    private const int _retries = 5;
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
    private const int _maxQueueSize = 1024 * 1024 * 999; // 999MB

    /// <summary>
    /// variable to hold the current size of the dead letter queue
    /// </summary>
    private int _dlqSize;

    /// <summary>
    /// variable to hold the current size of the event buffer
    /// </summary>
    private int _ebSize;

    /// <summary>
    /// dictionary to hold timestamps of when messages were added to the dlq with topic as the value
    /// </summary>
    /// <remarks>this is used to remove the oldest message from the queue when the queue is full</remarks>
    private readonly Dictionary<DateTime, string> _dlqTimestamps = new();

    /// <summary>
    /// dictionary to hold timestamps of when messages were added to the eb with topic as the value
    /// </summary>
    /// <remarks>this is used to remove the oldest message from the queue when the queue is full</remarks>
    private readonly Dictionary<DateTime, string> _ebTimestamps = new();

    private readonly ILogger<MessageRegistryGrain> _logger = logger;

    // <inheritdoc />
    public async Task AddMessageToDeadLetterQueueAsync(string topic, CloudEvent message)
    {
        var size = CheckMessageSize(dlq, topic, message);
        if (size == 0 ){ return; }
        if (_dlqSize + size > _maxQueueSize)
        {
            // remove the oldest message from the queue - get the oldest timestamp
            var oldestTimestampTopic = _dlqTimestamps.OrderBy(x => x.Key).FirstOrDefault().Value;
            // remove the message from the queue
            var removedMessages = await RemoveMessageAsync(oldestTimestampTopic);
            // update the oldest timestamp
            _dlqTimestamps.Remove(_dlqTimestamps.OrderBy(x => x.Key).FirstOrDefault().Key);
        }
        await TryWriteMessageAsync(dlq, topic, message).ConfigureAwait(true);
        _dlqSize += size;
    }

    ///<inheritdoc />
    public async Task AddMessageToEventBufferAsync(string topic, CloudEvent message)
    {
        var size = CheckMessageSize(eb, topic, message);
        if (size == 0) { return; }
        if (_ebSize + size > _maxQueueSize)
        {
            // remove the oldest message from the queue - get the oldest timestamp
            var oldestTimestampTopic = _ebTimestamps.OrderBy(x => x.Key).FirstOrDefault().Value;
            // remove the message from the queue
            var removedMessages = await RemoveMessageAsync(oldestTimestampTopic);
            // update the oldest timestamp
            _ebTimestamps.Remove(_ebTimestamps.OrderBy(x => x.Key).FirstOrDefault().Key);
        }
        await TryWriteMessageAsync(eb, topic, message).ConfigureAwait(true);
        _ebSize += size;
        // Schedule the removal task to run in the background after bufferTime
        RemoveMessageAfterDelayAsync(size, topic, message).Ignore();
    }

    /// <summary>
    /// remove only the first message from the buffer for a given topic
    /// </summary>
    /// <param name="topic"></param>
    /// <returns>ValueTask<bool></returns>
    private async ValueTask<bool> RemoveMessageAsync(string topic)
    {
        if (state.State.DeadLetterQueue != null && state.State.DeadLetterQueue.TryGetValue(topic, out List<CloudEvent>? letters))
        {
            if (letters != null && letters.Count > 0)
            {
                var message = letters[0];
                letters.RemoveAt(0);
                state.State.DeadLetterQueue.AddOrUpdate(topic, letters, (_, _) => letters);
                // update the size of the queue
                _dlqSize -= message.CalculateSize();
                await _stateManager.WriteStateAsync().ConfigureAwait(true);
                return true;
            }
        }
        return false;
    }

    /// <summary>
    /// remove a specific message from the buffer for a given topic
    /// </summary>
    /// <param name="topic"></param>
    /// <param name="message"></param>
    /// <returns>ValueTask<bool></returns>
    private async ValueTask<bool> RemoveMessageAsync(string topic, CloudEvent message)
    {
        if (state.State.EventBuffer != null && state.State.EventBuffer.TryGetValue(topic, out List<CloudEvent>? events))
        {
            if (events != null && events.Remove(message))
            {
                state.State.EventBuffer.AddOrUpdate(topic, events, (_, _) => events);
                await _stateManager.WriteStateAsync().ConfigureAwait(true);
                return true;
            }
        }
        return false;
    }

    /// <summary>
    /// remove a specific message from the buffer for a given topic after a delay
    /// </summary>
    /// <param name="topic"></param>
    /// <param name="message"></param>
    private async Task RemoveMessageAfterDelayAsync(int size, string topic, CloudEvent message)
    {
        await Task.Delay(_bufferTime);
        await RemoveMessageAsync(topic, message);
        _ebSize -= size;
    }

    /// <summary>
    /// check the size of the message
    /// </summary>
    /// <param name="topic"></param>
    /// <param name="message"></param>
    /// <returns>ValueTask<bool></returns>
    private int CheckMessageSize(string whichQueue, string topic, CloudEvent message)
    {
        var size = message.CalculateSize();
        if (size > _maxMessageSize)
        {
            _logger.LogWarning($"Message size {size} for topic {topic} exceeds maximum size {_maxMessageSize}. This message will not be written to the {whichQueue}.");
            return 0;
        }
        return size;
    }

    /// <summary>
    /// Tries to write a message to the given queue in Orleans state.
    /// Allows for retries using etag for optimistic concurrency.
    /// </summary>
    /// <param name="whichQueue"></param>
    /// <param name="topic"></param>
    /// <param name="message"></param>
    /// <returns></returns>
    /// <exception cref="InvalidOperationException"></exception>
    private async ValueTask<bool> TryWriteMessageAsync(string whichQueue, string topic, CloudEvent message)
    {
        var retries = _retries;
        while (!await WriteMessageAsync(whichQueue, topic, message, state.Etag).ConfigureAwait(false))
        {
            if (retries-- <= 0)
            {
                throw new InvalidOperationException($"Failed to write MessageRegistryState after {_retries} retries.");
            }
            _logger.LogWarning("Failed to write MessageRegistryState. Retrying...");
            retries--;
        }
        if (retries == 0) { return false; } else 
        {
            if (whichQueue == dlq) { _dlqTimestamps.Add(DateTime.UtcNow, topic); }
            else if (whichQueue == eb) { _ebTimestamps.Add(DateTime.UtcNow, topic); }
            return true;
        }
    }
    /// <summary>
    /// Writes a message to the given queue in Orleans state.
    /// </summary>
    /// <param name="whichQueue"></param>
    /// <param name="topic"></param>
    /// <param name="message"></param>
    /// <param name="etag"></param>
    /// <returns>ValueTask<bool></returns>
    /// <exception cref="ArgumentException"></exception>
    private async ValueTask<bool> WriteMessageAsync(string whichQueue, string topic, CloudEvent message, string etag)
    {
        if (state.Etag != null && state.Etag != etag)
        {
            return false;
        }
        switch (whichQueue)
        {
            case dlq:
                var dlqQueue = state.State.DeadLetterQueue.GetOrAdd(topic, _ => new());
                dlqQueue.Add(message);
                state.State.DeadLetterQueue.AddOrUpdate(topic, dlqQueue, (_, _) => dlqQueue);
                break;
            case eb:
                var ebQueue = state.State.EventBuffer.GetOrAdd(topic, _ => new());
                ebQueue.Add(message);
                state.State.EventBuffer.AddOrUpdate(topic, ebQueue, (_, _) => ebQueue);
                break;
            default:
                throw new ArgumentException($"Invalid queue name: {whichQueue}");
        }
        await _stateManager.WriteStateAsync().ConfigureAwait(true);
        return true;
    }

    // <inheritdoc />
    public async Task<List<CloudEvent>> RemoveMessagesAsync(string topic)
    {
        var messages = new List<CloudEvent>();
        if (state.State.DeadLetterQueue != null && state.State.DeadLetterQueue.Remove(topic, out List<CloudEvent>? letters))
        {
            await _stateManager.WriteStateAsync().ConfigureAwait(true);
            if (letters != null)
            {
                messages.AddRange(letters);
            }
        }
        if (state.State.EventBuffer != null && state.State.EventBuffer.Remove(topic, out List<CloudEvent>? events))
        {
            await _stateManager.WriteStateAsync().ConfigureAwait(true);
            if (events != null)
            {
                messages.AddRange(events);
            }
        }
        return messages;
    }
}
