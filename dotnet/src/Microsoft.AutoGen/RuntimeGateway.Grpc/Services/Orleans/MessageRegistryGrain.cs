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
    private readonly ILogger<MessageRegistryGrain> _logger = logger;

    // <inheritdoc />
    public async Task AddMessageToDeadLetterQueueAsync(string topic, CloudEvent message)
    {
        await TryWriteMessageAsync("dlq", topic, message).ConfigureAwait(true);
    }

    ///<inheritdoc />
    public async Task AddMessageToEventBufferAsync(string topic, CloudEvent message)
    {
        await TryWriteMessageAsync("eb", topic, message).ConfigureAwait(true);
        // Schedule the removal task to run in the background after bufferTime
        RemoveMessageAfterDelay(topic, message).Ignore();
    }

    /// <summary>
    /// remove a specific message from the buffer for a given topic
    /// </summary>
    /// <param name="topic"></param>
    /// <param name="message"></param>
    /// <returns>ValueTask<bool></returns>
    private async ValueTask<bool> RemoveMessage(string topic, CloudEvent message)
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
    private async Task RemoveMessageAfterDelay(string topic, CloudEvent message)
    {
        await Task.Delay(_bufferTime);
        await RemoveMessage(topic, message);
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
        if (retries == 0) { return false; } else { return true; }
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
            case "dlq":
                var dlqQueue = state.State.DeadLetterQueue.GetOrAdd(topic, _ => new());
                dlqQueue.Add(message);
                state.State.DeadLetterQueue.AddOrUpdate(topic, dlqQueue, (_, _) => dlqQueue);
                break;
            case "eb":
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
