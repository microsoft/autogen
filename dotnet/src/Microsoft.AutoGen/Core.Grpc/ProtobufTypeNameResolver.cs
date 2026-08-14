// Copyright (c) Microsoft Corporation. All rights reserved.
// ProtobufTypeNameResolver.cs

using Google.Protobuf;

namespace Microsoft.AutoGen.Core.Grpc;

public class ProtobufTypeNameResolver : ITypeNameResolver
{
    public string ResolveTypeName(Type input)
    {
        if (typeof(IMessage).IsAssignableFrom(input))
        {
            // TODO: Consider changing this to avoid instantiation...
            var protoMessage = (IMessage?)Activator.CreateInstance(input) ?? throw new InvalidOperationException($"Failed to create instance of {input.FullName}");
            return protoMessage.Descriptor.FullName;
        }
        else
        {
            throw new ArgumentException("Input must be a protobuf message.");
        }
    }
}
