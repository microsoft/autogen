// Copyright (c) Microsoft Corporation. All rights reserved.
// SerializationRegistry.cs

namespace Microsoft.AutoGen.Core.Grpc;

public class ProtoSerializationRegistry : IProtoSerializationRegistry
{
    private readonly Dictionary<Type, IProtoMessageSerializer> _serializers
        = new Dictionary<Type, IProtoMessageSerializer>();

    public bool Exists(Type type)
    {
        return _serializers.ContainsKey(type);
    }

    public IProtoMessageSerializer? GetSerializer(Type type)
    {
        _serializers.TryGetValue(type, out var serializer);
        return serializer;
    }

    public void RegisterSerializer(Type type, IProtoMessageSerializer serializer)
    {
        if (_serializers.ContainsKey(type))
        {
            throw new InvalidOperationException($"Serializer already registered for {type.FullName}");
        }
        _serializers[type] = serializer;
    }
}
