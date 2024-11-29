// Copyright (c) Microsoft Corporation. All rights reserved.
// OrleansRuntimeHostingExtenions.cs

using Microsoft.AspNetCore.Builder;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Orleans.Serialization;

namespace Microsoft.AutoGen.DistributedRuntime;

public static class OrleansRuntimeHostingExtenions
{
    public static WebApplicationBuilder AddOrleans(this WebApplicationBuilder builder, bool inMemory = false)
    {
        builder.Services.AddSerializer(serializer => serializer.AddProtobufSerializer());
        builder.Services.AddSingleton<IRegistryGrain, RegistryGrain>();

        // Ensure Orleans is added before the hosted service to guarantee that it starts first.
        //TODO: make all of this configurable
        builder.UseOrleans((siloBuilder) =>
        {
            // Development mode or local mode uses in-memory storage and streams

                siloBuilder.UseLocalhostClustering()
                       .AddMemoryStreams("StreamProvider")
                       .AddMemoryGrainStorage("PubSubStore")
                       .AddMemoryGrainStorage("AgentStateStore");

                siloBuilder.UseInMemoryReminderService();
            //TODO: Add pass through config for state and streams
        });

        return builder;
    }
}
