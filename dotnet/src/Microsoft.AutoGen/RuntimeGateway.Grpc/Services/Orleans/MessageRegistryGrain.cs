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
    private const int _retries = 5;
    private readonly ILogger<MessageRegistryGrain> _logger = logger;

    public async Task AddMessageToDeadLetterQueueAsync(string topic, CloudEvent message)
    {
        await TryWriteMessageAsync("dlq", topic, message).ConfigureAwait(true);
    }
    public async Task AddMessageToEventBufferAsync(string topic, CloudEvent message)
    {
        await TryWriteMessageAsync("eb", topic, message).ConfigureAwait(true);
    }
    private async ValueTask<bool> TryWriteMessageAsync(string whichQueue, string topic, CloudEvent message)
    {
        var retries = _retries;
        while (!await WriteMessageAsync(whichQueue,topic, message, state.Etag).ConfigureAwait(false))
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
        await state.WriteStateAsync().ConfigureAwait(true);
        return true;
    }

    public async Task<List<CloudEvent>> RemoveMessagesAsync(string topic)
    {
        if (state.State.DeadLetterQueue != null && state.State.DeadLetterQueue.Remove(topic, out List<CloudEvent>? letters))
        {
            await state.WriteStateAsync().ConfigureAwait(true);
            if (letters != null)
            {
                return letters;
            }
        }
        return [];
    }
}
