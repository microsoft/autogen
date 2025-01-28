// Copyright (c) Microsoft Corporation. All rights reserved.
// ProtoSerializationRegistry.cs

namespace Microsoft.AutoGen.Core.Grpc;

public class ProtoSerializationRegistry : IProtoSerializationRegistry
{
    private readonly Dictionary<string, IProtoMessageSerializer> _serializers
        = new Dictionary<string, IProtoMessageSerializer>();

    public ITypeNameResolver TypeNameResolver =>  new ProtoTypeNameResolver();

    public bool Exists(Type type)
    {
        return _serializers.ContainsKey(TypeNameResolver.ResolveTypeName(type));
    }

    public IProtoMessageSerializer? GetSerializer(Type type)
    {
        return GetSerializer(TypeNameResolver.ResolveTypeName(type));
    }

    public IProtoMessageSerializer? GetSerializer(string typeName)
    {
        _serializers.TryGetValue(typeName, out var serializer);
        return serializer;
    }

    public void RegisterSerializer(Type type, IProtoMessageSerializer serializer)
    {
        if (_serializers.ContainsKey(TypeNameResolver.ResolveTypeName(type)))
        {
            throw new InvalidOperationException($"Serializer already registered for {type.FullName}");
        }
        _serializers[TypeNameResolver.ResolveTypeName(type)] = serializer;
    }
}
