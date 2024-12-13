// Copyright (c) Microsoft Corporation. All rights reserved.
// InMemoryAgentRuntimeFixture.cs

using System.Diagnostics;
using Microsoft.AutoGen.Contracts;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;
using Moq;

namespace Microsoft.AutoGen.Core.Tests.Helpers;

public sealed class InMemoryAgentRuntimeFixture : IDisposable
{
    public InMemoryAgentRuntimeFixture()
    {
        var builder = Host.CreateApplicationBuilder();
        // step 1: create in-memory agent runtime
        // step 2: register TestAgent to that agent runtime
        builder
            .AddInMemoryWorker()
            .AddAgentHost()
            .AddAgent<TestAgent>(nameof(TestAgent));

        AppHost = builder.Build();
        AppHost.StartAsync().Wait();
    }
    public IHost AppHost { get; }

    void IDisposable.Dispose()
    {
        AppHost.StopAsync().Wait();
        AppHost.Dispose();
    }

    public RuntimeContext CreateContext(AgentId agentId)
    {
        var agentWorker = AppHost.Services.GetRequiredService<IAgentWorker>();
        var dctx = Mock.Of<DistributedContextPropagator>();
        var logger = Mock.Of<ILogger<Agent>>();
        return new RuntimeContext(agentId, agentWorker, logger, dctx);
    }
}
