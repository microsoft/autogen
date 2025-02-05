// Copyright (c) Microsoft Corporation. All rights reserved.
// IAgentMessageSerializer.cs

namespace Microsoft.AutoGen.Core.Grpc;
/// <summary>
/// Interface for serializing and deserializing agent messages.
/// </summary>
public interface IAgentMessageSerializer
{
    /// <summary>
    /// Serialize an agent message.
    /// </summary>
    /// <param name="message">The message to serialize.</param>
    /// <returns>The serialized message.</returns>
    Google.Protobuf.WellKnownTypes.Any Serialize(object message);

    /// <summary>
    /// Deserialize an agent message.
    /// </summary>
    /// <param name="message">The message to deserialize.</param>
    /// <returns>The deserialized message.</returns>
    object Deserialize(Google.Protobuf.WellKnownTypes.Any message);
}
