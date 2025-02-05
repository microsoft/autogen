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
    public AgentsApp? Client { get; private set; }
    /// mock server for testing.
    public WebApplication? Server { get; private set; }

    public GrpcAgentRuntimeFixture()
    {
    }
    /// <summary>
    /// Start - gets a new port and starts fresh instances
    /// </summary>
    public async Task<IAgentRuntime> Start(bool initialize = true)
    {
        int port = GetAvailablePort(); // Get a new port per test run

        // Update environment variables so each test runs independently
        Environment.SetEnvironmentVariable("ASPNETCORE_HTTPS_PORTS", port.ToString());
        Environment.SetEnvironmentVariable("AGENT_HOST", $"https://localhost:{port}");
        Environment.SetEnvironmentVariable("ASPNETCORE_ENVIRONMENT", "Development");
        Server = ServerBuilder().Result;
        await Server.StartAsync().ConfigureAwait(true);
        Client = ClientBuilder().Result;
        await Client.StartAsync().ConfigureAwait(true);

        var worker = Client.Services.GetRequiredService<IAgentRuntime>();

        return (worker);
    }
    private static async Task<AgentsApp> ClientBuilder()
    {
        var appBuilder = new AgentsAppBuilder();
        appBuilder.AddGrpcAgentWorker();
        appBuilder.AddAgent<TestProtobufAgent>("TestAgent");
        return await appBuilder.BuildAsync();
    }
    private static async Task<WebApplication> ServerBuilder()
    {
        var builder = WebApplication.CreateBuilder();
        builder.Services.AddGrpc();
        var app = builder.Build();
        app.MapGrpcService<GrpcAgentServiceFixture>();
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
        (Client as IHost)?.StopAsync(TimeSpan.FromSeconds(30)).GetAwaiter().GetResult();
        Server?.StopAsync().GetAwaiter().GetResult();
    }

    /// <summary>
    /// Dispose - Ensures cleanup after each test
    /// </summary>
    public void Dispose()
    {
        Stop();
    }

}
