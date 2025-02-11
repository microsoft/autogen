// Copyright (c) Microsoft Corporation. All rights reserved.
// GrpcAgentRuntimeFixture.cs
using Microsoft.AspNetCore.Builder;
using Microsoft.AutoGen.Contracts;
// using Microsoft.AutoGen.Core.Tests;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;

namespace Microsoft.AutoGen.Core.Grpc.Tests;

/// <summary>
/// Fixture for setting up the gRPC agent runtime for testing.
/// </summary>
public sealed class GrpcAgentRuntimeFixture : IDisposable
{
    /// the gRPC agent runtime.
    public AgentsApp? AgentsApp { get; private set; }

    /// mock server for testing.
    public WebApplication? GatewayServer { get; private set; }

    public GrpcAgentServiceCollector GrpcRequestCollector { get; }

    public GrpcAgentRuntimeFixture()
    {
        GrpcRequestCollector = new GrpcAgentServiceCollector();
    }

    /// <summary>
    /// Start - gets a new port and starts fresh instances
    /// </summary>
    public async Task<IAgentRuntime> Start(bool startRuntime = true, bool registerDefaultAgent = true)
    {
        int port = GetAvailablePort(); // Get a new port per test run

        // Update environment variables so each test runs independently
        Environment.SetEnvironmentVariable("ASPNETCORE_HTTPS_PORTS", port.ToString());
        Environment.SetEnvironmentVariable("AGENT_HOST", $"https://localhost:{port}");
        Environment.SetEnvironmentVariable("ASPNETCORE_ENVIRONMENT", "Development");

        this.GatewayServer = await this.InitializeGateway();
        this.AgentsApp = await this.InitializeRuntime(startRuntime, registerDefaultAgent);
        var runtime = AgentsApp.Services.GetRequiredService<IAgentRuntime>();

        return runtime;
    }

    private async Task<AgentsApp> InitializeRuntime(bool callStartAsync, bool registerDefaultAgent)
    {
        var appBuilder = new AgentsAppBuilder();
        appBuilder.AddGrpcAgentWorker();

        if (registerDefaultAgent)
        {
            appBuilder.AddAgent<TestProtobufAgent>("TestAgent");
        }

        AgentsApp result = await appBuilder.BuildAsync();

        if (callStartAsync)
        {
            await result.StartAsync().ConfigureAwait(true);
        }

        return result;
    }

    private async Task<WebApplication> InitializeGateway()
    {
        var builder = WebApplication.CreateBuilder();
        builder.Services.AddGrpc();
        builder.Services.AddSingleton(this.GrpcRequestCollector);

        WebApplication app = builder.Build();
        app.MapGrpcService<GrpcAgentServiceFixture>();

        await app.StartAsync().ConfigureAwait(true);
        return app;
    }

    private static int GetAvailablePort()
    {
        using var listener = new System.Net.Sockets.TcpListener(System.Net.IPAddress.Loopback, 0);
        listener.Start();
        int port = ((System.Net.IPEndPoint)listener.LocalEndpoint).Port;
        listener.Stop();
        return port;
    }

    /// <summary>
    /// Stop - stops the agent and ensures cleanup
    /// </summary>
    public void Stop()
    {
        (AgentsApp as IHost)?.StopAsync(TimeSpan.FromSeconds(30)).GetAwaiter().GetResult();
        GatewayServer?.StopAsync().GetAwaiter().GetResult();
    }

    /// <summary>
    /// Dispose - Ensures cleanup after each test
    /// </summary>
    public void Dispose()
    {
        Stop();
    }

}
