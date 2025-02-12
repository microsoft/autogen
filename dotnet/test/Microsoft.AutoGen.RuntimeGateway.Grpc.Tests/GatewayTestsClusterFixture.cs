// Copyright (c) Microsoft Corporation. All rights reserved.
// GatewayTestsClusterFixture.cs
using Microsoft.Extensions.Configuration;
using Orleans.TestingHost;

namespace Microsoft.AutoGen.RuntimeGateway.Grpc.Tests;

public class GatewayTestClusterFixture : IDisposable
{
    public TestCluster Cluster { get; }

    public GatewayTestClusterFixture()
    {
        var builder = new TestClusterBuilder();
        builder.ConfigureHostConfiguration(config =>
        {
            config.AddInMemoryCollection(new Dictionary<string, string?>
            {
                ["PubSubStore"] = "UseDevelopmentStorage=true"
            });
        });
        builder.AddSiloBuilderConfigurator<SiloConfigurator>();
        Cluster = builder.Build();
        Cluster.Deploy();
    }

    public void Dispose()
    {
        Cluster.StopAllSilos();
    }

    private class SiloConfigurator : ISiloConfigurator
    {
        public void Configure(ISiloBuilder siloBuilder)
        {
            siloBuilder.AddAzureTableGrainStorage("PubSubStore", options =>
            {
                options.UseDevelopmentStorage = true;
            });
        }
    }
}
