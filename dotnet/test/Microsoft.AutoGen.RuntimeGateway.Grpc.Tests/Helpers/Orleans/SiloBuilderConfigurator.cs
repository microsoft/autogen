// Copyright (c) Microsoft Corporation. All rights reserved.
// SiloBuilderConfigurator.cs

using Orleans.Serialization;
using Orleans.TestingHost;

namespace Microsoft.AutoGen.RuntimeGateway.Grpc.Tests.Helpers.Orleans;

public class SiloBuilderConfigurator : ISiloConfigurator
{
    public void Configure(ISiloBuilder siloBuilder)
    {
        siloBuilder.ConfigureServices(services =>
        {
            services.AddSerializer(a => a.AddProtobufSerializer());
        });
        siloBuilder.AddMemoryStreams("StreamProvider")
            .AddMemoryGrainStorage("PubSubStore")
            .AddMemoryGrainStorage("AgentRegistryStore")
            .AddMemoryGrainStorage("AgentStateStore");
    }
}
