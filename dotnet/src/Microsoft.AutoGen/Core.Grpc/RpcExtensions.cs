// Copyright (c) Microsoft Corporation. All rights reserved.
// RpcExtensions.cs

using Google.Protobuf;
using Microsoft.AutoGen.Protobuf;

namespace Microsoft.AutoGen.Core.Grpc;

internal static class RpcExtensions
{

    public static Payload ToPayload(this object message, IProtoSerializationRegistry serializationRegistry)
    {
        if (!serializationRegistry.Exists(message.GetType()))
        {
            serializationRegistry.RegisterSerializer(message.GetType());
        }
        var rpcMessage = (serializationRegistry.GetSerializer(message.GetType()) ?? throw new Exception()).Serialize(message);

        var typeName = serializationRegistry.TypeNameResolver.ResolveTypeName(message.GetType());
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

    public static object ToObject(this Payload payload, IProtoSerializationRegistry serializationRegistry)
    {
        var typeName = payload.DataType;
        var data = payload.Data;
        var serializer = serializationRegistry.GetSerializer(typeName) ?? throw new Exception();
        var any = Google.Protobuf.WellKnownTypes.Any.Parser.ParseFrom(data);
        return serializer.Deserialize(any);
    }
}
