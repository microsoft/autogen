// Copyright (c) Microsoft Corporation. All rights reserved.
// ClusterCollection.cs

namespace Microsoft.AutoGen.Runtime.Grpc.Tests.Helpers.Orleans;

[CollectionDefinition(Name)]
public sealed class ClusterCollection : ICollectionFixture<ClusterFixture>
{
    public const string Name = nameof(ClusterCollection);
}
