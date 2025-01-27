// Copyright (c) Microsoft Corporation. All rights reserved.
// InMemoryAgentRuntimeFixture.cs
using System.Diagnostics;
using Microsoft.AutoGen.Contracts;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.DependencyInjection.Extensions;
using Microsoft.Extensions.Hosting;
namespace Microsoft.AutoGen.Core.Tests;
/// <summary>
/// InMemoryAgentRuntimeFixture - provides a fixture for the agent runtime.
/// </summary>
/// <remarks>
/// This fixture is used to provide a runtime for the agent tests.
/// However, it is shared between tests. So operations from one test can affect another.
/// </remarks>
public sealed class InMemoryAgentRuntimeFixture : IDisposable
{
    public InMemoryAgentRuntimeFixture()
    {
        var builder = new HostApplicationBuilder();
        builder.Services.TryAddSingleton(DistributedContextPropagator.Current);
        builder.AddAgentWorker()
            .AddAgent<TestAgent>(nameof(TestAgent));
        AppHost = builder.Build();
        AppHost.StartAsync().Wait();
    }
    public IHost AppHost { get; }

    /// <summary>
    /// Start - starts the agent
    /// </summary>
    /// <returns>IAgentWorker, TestAgent</returns>
    public (IAgentRuntime, TestAgent) Start()
    {
        var agent = ActivatorUtilities.CreateInstance<TestAgent>(AppHost.Services);
        var worker = AppHost.Services.GetRequiredService<IAgentRuntime>();
        Agent.Initialize(worker, agent);
        return (worker, agent);
    }
    /// <summary>
    /// Stop - stops the agent and ensures cleanup
    /// </summary>
    public void Stop()
    {
        AppHost?.StopAsync().GetAwaiter().GetResult();
    }

    /// <summary>
    /// Dispose - Ensures cleanup after each test
    /// </summary>
    public void Dispose()
    {
        Stop();
    }
}
