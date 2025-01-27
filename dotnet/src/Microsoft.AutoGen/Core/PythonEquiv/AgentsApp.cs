// Copyright (c) Microsoft Corporation. All rights reserved.
// AgentsApp.cs

using Microsoft.AutoGen.Contracts.Python;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;

namespace Microsoft.AutoGen.Core.PythonEquiv;

public class AgentsAppBuilder
{
    private List<Func<AgentsApp, ValueTask<AgentType>>> AgentTypeRegistrations { get; } = new();

    private readonly HostApplicationBuilder builder;

    public AgentsAppBuilder(HostApplicationBuilder? baseBuilder = null)
    {
        this.builder = baseBuilder ?? new HostApplicationBuilder();
    }

    public void AddAgent<TAgent>(string name, bool skipClassSubscriptions = false, bool skipDirectMessageSubscription = false) where TAgent : IHostableAgent
    {
        this.AgentTypeRegistrations.Add(async app => {
            var agentType = await app.AgentRuntime.RegisterAgentTypeAsync<TAgent>(name, app.Services);
            await app.AgentRuntime.RegisterImplicitAgentSubscriptionsAsync<TAgent>(name, skipClassSubscriptions, skipDirectMessageSubscription);
            return agentType;
        });
    }

    public async ValueTask<AgentsApp> BuildAsync()
    {
        IHost host = this.builder.Build();
        AgentsApp app = new AgentsApp(host);

        foreach (var registration in this.AgentTypeRegistrations)
        {
            await registration(app);
        }

        return app;
    }
}

public class AgentsApp
{
    public AgentsApp(IHost host)
    {
        this.Host = host;
    }

    public IHost Host { get; private set; }

    public IServiceProvider Services => this.Host.Services;

    public IAgentRuntime AgentRuntime => this.Services.GetRequiredService<IAgentRuntime>();

    public async ValueTask StartAsync() => await this.Host.StartAsync();

    public async ValueTask ShutdownAsync() => await this.Host.StopAsync();

    public ValueTask PublishMessageAsync<TMessage>(TMessage message, string topic, string? messageId = null, CancellationToken? cancellationToken = default)
        where TMessage : notnull
        => this.AgentRuntime.PublishMessageAsync(message, TopicId.FromStr(topic), messageId: messageId, cancellationToken: cancellationToken);

    public ValueTask PublishMessageAsync<TMessage>(TMessage message, TopicId topic, string? messageId = null, CancellationToken? cancellationToken = default)
        where TMessage : notnull
    {
        return this.AgentRuntime.PublishMessageAsync(message, topic, messageId: messageId, cancellationToken: cancellationToken);
    }

    public Task WaitForShutdownAsync()
    {
        return this.Host.WaitForShutdownAsync();
    }
}
