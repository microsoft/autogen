// Copyright (c) Microsoft Corporation. All rights reserved.
// ProtoTypeNameResolver.cs

using Google.Protobuf;

namespace Microsoft.AutoGen.Core.Grpc;

public class ProtoTypeNameResolver : ITypeNameResolver
{
    public string ResolveTypeName(object input)
    {
        if (input is IMessage protoMessage)
        {
            return protoMessage.Descriptor.FullName;
        }
        else
        {
            throw new ArgumentException("Input must be a protobuf message.");
        }
    }
}
