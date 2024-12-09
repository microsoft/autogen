// Copyright (c) Microsoft Corporation. All rights reserved.
// ClusterFixtureCollection.cs

using Xunit;

namespace Microsoft.AutoGen.Core.Tests.Helpers;

[CollectionDefinition(Name)]
public sealed class CoreFixtureCollection : ICollectionFixture<InMemoryAgentRuntimeFixture>
{
    public const string Name = nameof(CoreFixtureCollection);
}
