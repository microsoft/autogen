// Copyright (c) Microsoft Corporation. All rights reserved.
// ClusterFixture.cs

using Orleans.TestingHost;

namespace Microsoft.AutoGen.RuntimeGateway.Grpc.Tests.Helpers.Orleans;

public sealed class ClusterFixture : IDisposable
{
    public ClusterFixture()
    {
        var builder = new TestClusterBuilder();
        builder.AddSiloBuilderConfigurator<SiloBuilderConfigurator>();
        Cluster = builder.Build();
        Cluster.Deploy();

    }
    public TestCluster Cluster { get; }

    void IDisposable.Dispose() => Cluster.StopAllSilos();
}
