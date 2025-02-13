// Copyright (c) Microsoft Corporation. All rights reserved.
// ITypeNameResolver.cs

namespace Microsoft.AutoGen.Core.Grpc;

public interface ITypeNameResolver
{
    string ResolveTypeName(Type input);
}
