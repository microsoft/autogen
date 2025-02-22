// Copyright (c) Microsoft Corporation. All rights reserved.
// MessageRegistryQueue.cs

using System.Collections.Concurrent;
using Microsoft.AutoGen.Contracts;
using Microsoft.AutoGen.RuntimeGateway.Grpc.Abstractions;
using Microsoft.Extensions.Logging;

namespace Microsoft.AutoGen.RuntimeGateway.Grpc;

public sealed class MessageRegistryQueue
{
    private ConcurrentDictionary<string, List<CloudEvent>> _queue = new();
    private readonly int _maxMessageSize;
    private readonly int _maxQueueSize;
    private readonly Dictionary<DateTime, string> _timestamps = new();
    private int _currentSize;
    private readonly IPersistentState<MessageRegistryState> _state;
    private readonly ILogger _logger;
    private readonly StateManager _stateManager;
    private readonly MessageRegistryGrain.QueueType _queueType;

    internal MessageRegistryQueue(MessageRegistryGrain.QueueType queueType,
        IPersistentState<MessageRegistryState> state,
        StateManager stateManager,
        ILogger logger,
        int maxMessageSize,
        int maxQueueSize)
    {
        if (state.State == null)
        {
            state.State = new MessageRegistryState();
        }
        _queueType = queueType;
        _state = state;
        // use the queueType to get the correct queue from state.State.
        _queue = GetQueue();
        _stateManager = stateManager;
        _logger = logger;
        _maxMessageSize = maxMessageSize;
        _maxQueueSize = maxQueueSize;
    }

    public async Task AddMessageAsync(string topic, CloudEvent message)
    {
        var size = message.CalculateSize();
        if (size > _maxMessageSize)
        {
            _logger.LogWarning("Message size {Size} for topic {Topic} in queue {Name} exceeds the maximum message size {Max}.",
                size, topic, _queueType.ToString(), _maxMessageSize);
            return;
        }
        if (_currentSize + size > _maxQueueSize)
        {
            while (_currentSize + size > _maxQueueSize && _timestamps.Count > 0)
            {
                var oldest = _timestamps.OrderBy(x => x.Key).First();
                if (await RemoveOldestMessage(oldest.Value))
                {
                    _timestamps.Remove(oldest.Key);
                }
            }
        }
        await AddOrUpdate(topic, message);
        _currentSize += size;
    }

    public async Task<List<CloudEvent>> RemoveMessagesAsync(string topic)
    {
        var removed = new List<CloudEvent>();
        var queue = GetQueue();
        if (queue.Remove(topic, out var events))
        {
            removed.AddRange(events);
            var total = 0;
            foreach (var e in events) { total += e.CalculateSize(); }
            _currentSize -= total;
        }
        // Remove timestamps that refer to this topic
        var toRemove = _timestamps.Where(x => x.Value == topic).Select(x => x.Key).ToList();
        foreach (var t in toRemove) { _timestamps.Remove(t); }
        await _stateManager.WriteStateAsync().ConfigureAwait(true);
        return removed;
    }

    public async Task<bool> RemoveMessageAsync(string topic, CloudEvent message)
    {
        var queue = GetQueue();
        if (queue.TryGetValue(topic, out var events) && events.Remove(message))
        {
            _currentSize -= message.CalculateSize();
            await _stateManager.WriteStateAsync().ConfigureAwait(true);
            return true;
        }
        return false;
    }

    private async Task<bool> RemoveOldestMessage(string topic)
    {
        var queue = GetQueue();
        if (queue.TryGetValue(topic, out var events) && events != null && events.Count > 0)
        {
            var oldestEvent = events[0];
            events.RemoveAt(0);
            _currentSize -= oldestEvent.CalculateSize();
            _timestamps.Remove(_timestamps.OrderBy(x => x.Key).First().Key);
            queue[topic] = events;
            await _stateManager.WriteStateAsync().ConfigureAwait(true);
            return true;
        }
        return false;
    }

    private async Task AddOrUpdate(string topic, CloudEvent message)
    {
        var queue = GetQueue();
        var list = queue.GetOrAdd(topic, _ => new());
        list.Add(message);
        queue.AddOrUpdate(topic, list, (_, _) => list);
        await _stateManager.WriteStateAsync().ConfigureAwait(true);
        _timestamps.Add(DateTime.UtcNow, topic);
    }

    private ConcurrentDictionary<string, List<CloudEvent>> GetQueue()
    {
        return _queueType switch
        {
            MessageRegistryGrain.QueueType.DeadLetterQueue => _state.State.DeadLetterQueue,
            MessageRegistryGrain.QueueType.EventBuffer => _state.State.EventBuffer,
            _ => throw new ArgumentException($"Invalid queue type: {_queueType}.")
        };
    }

    public async Task RemoveMessageAfterDelayAsync(string topic, CloudEvent message, int delay)
    {
        await Task.Delay(delay);
        await RemoveMessageAsync(topic, message);
        _currentSize -= message.CalculateSize();
    }
}
