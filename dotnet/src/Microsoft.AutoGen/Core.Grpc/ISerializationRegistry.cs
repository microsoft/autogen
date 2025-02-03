// Copyright (c) Microsoft Corporation. All rights reserved.
// ISerializationRegistry.cs

namespace Microsoft.AutoGen.Core.Grpc;

public interface IProtoSerializationRegistry
{
    /// <summary>
    /// Registers a serializer for the specified type.
    /// </summary>
    /// <param name="type">The type to register.</param>
    void RegisterSerializer(System.Type type) => RegisterSerializer(type, new ProtobufMessageSerializer(type));

    void RegisterSerializer(System.Type type, IProtobufMessageSerializer serializer);

    /// <summary>
    /// Gets the serializer for the specified type.
    /// </summary>
    /// <param name="type">The type to get the serializer for.</param>
    /// <returns>The serializer for the specified type.</returns>
    IProtobufMessageSerializer? GetSerializer(System.Type type) => GetSerializer(TypeNameResolver.ResolveTypeName(type));
    IProtobufMessageSerializer? GetSerializer(string typeName);

    ITypeNameResolver TypeNameResolver { get; }

    bool Exists(System.Type type);
}
