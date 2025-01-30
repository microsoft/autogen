// Copyright (c) Microsoft Corporation. All rights reserved.
// ISerializationRegistry.cs

using Google.Protobuf;
using Microsoft.AutoGen.Protobuf;

namespace Microsoft.AutoGen.Core.Grpc;

public interface IProtoSerializationRegistry
{
    /// <summary>
    /// Registers a serializer for the specified type.
    /// </summary>
    /// <param name="type">The type to register.</param>
    void RegisterSerializer(System.Type type) => RegisterSerializer(type, new ProtobufMessageSerializer(type));

    void RegisterSerializer(System.Type type, IProtoMessageSerializer serializer);

    /// <summary>
    /// Gets the serializer for the specified type.
    /// </summary>
    /// <param name="type">The type to get the serializer for.</param>
    /// <returns>The serializer for the specified type.</returns>
    IProtoMessageSerializer? GetSerializer(System.Type type) => GetSerializer(TypeNameResolver.ResolveTypeName(type));
    IProtoMessageSerializer? GetSerializer(string typeName);

    ITypeNameResolver TypeNameResolver { get; }

    bool Exists(System.Type type);
}

public static class SerializerRegistryExtensions
{
    public static Payload ObjectToPayload(this IProtoSerializationRegistry this_, object message)
    {
        if (!this_.Exists(message.GetType()))
        {
            this_.RegisterSerializer(message.GetType());
        }
        var rpcMessage = (this_.GetSerializer(message.GetType()) ?? throw new Exception()).Serialize(message);

        var typeName = this_.TypeNameResolver.ResolveTypeName(message);
        const string PAYLOAD_DATA_CONTENT_TYPE = "application/x-protobuf";

        // Protobuf any to byte array
        Payload payload = new()
        {
            DataType = typeName,
            DataContentType = PAYLOAD_DATA_CONTENT_TYPE,
            Data = rpcMessage.ToByteString()
        };

        return payload;
    }

    public static object PayloadToObject(this IProtoSerializationRegistry this_, Payload payload)
    {
        var typeName = payload.DataType;
        var data = payload.Data;
        var type = this_.TypeNameResolver.ResolveTypeName(typeName);
        var serializer = this_.GetSerializer(type) ?? throw new Exception();
        var any = Google.Protobuf.WellKnownTypes.Any.Parser.ParseFrom(data);
        return serializer.Deserialize(any);
    }
}
