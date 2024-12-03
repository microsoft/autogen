// Copyright (c) Microsoft Corporation. All rights reserved.
// ClusterFixtureCollection.cs

using Xunit;

namespace Microsoft.AutoGen.Core.Tests;

[CollectionDefinition(Name)]
public sealed class ClusterFixtureCollection : ICollectionFixture<InMemoryAgentRuntimeFixture>
{
    public const string Name = nameof(ClusterFixtureCollection);
}
