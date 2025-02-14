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

    public async Task WriteMessageAsync(string topic, CloudEvent message)
    {
        var retries = _retries;
        while (!await WriteMessageAsync(topic, message, state.Etag).ConfigureAwait(false))
        {
            if (retries-- <= 0)
            {
                throw new InvalidOperationException($"Failed to write MessageRegistryState after {_retries} retries.");
            }
            _logger.LogWarning("Failed to write MessageRegistryState. Retrying...");
            retries--;
        }
    }
    private async ValueTask<bool> WriteMessageAsync(string topic, CloudEvent message, string etag)
    {
        if (state.Etag != null && state.Etag != etag)
        {
            return false;
        }
        var queue = state.State.DeadLetterQueue.GetOrAdd(topic, _ => new());
        queue.Add(message);
        state.State.DeadLetterQueue.AddOrUpdate(topic, queue, (_, _) => queue);
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
