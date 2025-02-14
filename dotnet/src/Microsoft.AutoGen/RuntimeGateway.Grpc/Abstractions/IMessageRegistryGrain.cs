// Copyright (c) Microsoft Corporation. All rights reserved.
// IMessageRegistryGrain.cs

using Microsoft.AutoGen.Contracts;

namespace Microsoft.AutoGen.RuntimeGateway.Grpc.Abstractions;

public interface IMessageRegistryGrain : IGrainWithIntegerKey
{
    /// <summary>
    /// Writes a message to the dead-letter queue for the given topic.
    /// </summary>
    Task WriteMessageAsync(string topic, CloudEvent message);

    /// <summary>
    /// Removes all messages for the given topic from the dead-letter queue.
    /// </summary>
    /// <param name="topic">The topic to remove messages for.</param>
    /// <returns>A task representing the asynchronous operation, with the list of removed messages as the result.</returns>
    Task<List<CloudEvent>> RemoveMessagesAsync(string topic);
}

