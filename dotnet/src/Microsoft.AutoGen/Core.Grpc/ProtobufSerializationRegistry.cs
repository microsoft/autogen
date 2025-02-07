// Copyright (c) Microsoft Corporation. All rights reserved.
// ProtobufSerializationRegistry.cs

namespace Microsoft.AutoGen.Core.Grpc;

public class ProtobufSerializationRegistry : IProtoSerializationRegistry
{
    private readonly Dictionary<string, IProtobufMessageSerializer> _serializers
        = new Dictionary<string, IProtobufMessageSerializer>();

    public ITypeNameResolver TypeNameResolver => new ProtobufTypeNameResolver();

    public bool Exists(Type type)
    {
        return _serializers.ContainsKey(TypeNameResolver.ResolveTypeName(type));
    }

    public IProtobufMessageSerializer? GetSerializer(Type type)
    {
        return GetSerializer(TypeNameResolver.ResolveTypeName(type));
    }

    public IProtobufMessageSerializer? GetSerializer(string typeName)
    {
        _serializers.TryGetValue(typeName, out var serializer);
        return serializer;
    }

    public void RegisterSerializer(Type type, IProtobufMessageSerializer serializer)
    {
        if (_serializers.ContainsKey(TypeNameResolver.ResolveTypeName(type)))
        {
            throw new InvalidOperationException($"Serializer already registered for {type.FullName}");
        }
        _serializers[TypeNameResolver.ResolveTypeName(type)] = serializer;
    }
}
