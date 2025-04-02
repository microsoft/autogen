// Copyright (c) Microsoft Corporation. All rights reserved.
// ProtobufMessageSerializer.cs

using Google.Protobuf;
using Google.Protobuf.WellKnownTypes;

namespace Microsoft.AutoGen.Core.Grpc;

/// <summary>
/// Interface for serializing and deserializing agent messages.
/// </summary>
public class ProtobufMessageSerializer : IProtobufMessageSerializer
{
    private System.Type _concreteType;

    public ProtobufMessageSerializer(System.Type concreteType)
    {
        _concreteType = concreteType;
    }

    public object Deserialize(Any message)
    {
        // Check if the concrete type is a proto IMessage
        if (typeof(IMessage).IsAssignableFrom(_concreteType))
        {
            var nameOfMethod = nameof(Any.Unpack);
            var result = message.GetType().GetMethods().Where(m => m.Name == nameOfMethod && m.IsGenericMethod).First().MakeGenericMethod(_concreteType).Invoke(message, null);
            return result as IMessage ?? throw new ArgumentException("Failed to deserialize", nameof(message));
        }

        // Raise an exception if the concrete type is not a proto IMessage
        throw new ArgumentException("Concrete type must be a proto IMessage", nameof(_concreteType));
    }

    public Any Serialize(object message)
    {
        // Check if message is a proto IMessage
        if (message is IMessage protoMessage)
        {
            return Any.Pack(protoMessage);
        }

        // Raise an exception if the message is not a proto IMessage
        throw new ArgumentException("Message must be a proto IMessage", nameof(message));
    }
}
