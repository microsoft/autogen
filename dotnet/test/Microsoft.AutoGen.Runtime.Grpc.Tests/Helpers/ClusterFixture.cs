// Copyright (c) Microsoft Corporation. All rights reserved.
// ClusterFixture.cs

using Orleans.TestingHost;

namespace Microsoft.AutoGen.Runtime.Grpc.Tests.Helpers;

public sealed class ClusterFixture : IDisposable
{
    public TestCluster Cluster { get; } = new TestClusterBuilder().Build();

    public ClusterFixture() => Cluster.Deploy();

    void IDisposable.Dispose() => Cluster.StopAllSilos();
}
