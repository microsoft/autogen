// Copyright (c) Microsoft Corporation. All rights reserved.
// AgentsAppBuilderExtensions.cs

using Microsoft.AutoGen.Contracts;
using Microsoft.Extensions.DependencyInjection;

namespace Microsoft.AutoGen.Core.Grpc;

public static class AgentsAppBuilderExtensions
{
    public static AgentsAppBuilder UseGrpcRuntime(this AgentsAppBuilder this_, bool deliverToSelf = false)
    {
        this_.Services.AddSingleton<IAgentRuntime, GrpcAgentRuntime>();
        this_.Services.AddHostedService<GrpcAgentRuntime>(services =>
        {
            return (services.GetRequiredService<IAgentRuntime>() as GrpcAgentRuntime)!;
        });

        return this_;
    }
}
