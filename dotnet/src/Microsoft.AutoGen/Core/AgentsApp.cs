// Copyright (c) Microsoft Corporation. All rights reserved.
// AgentsApp.cs

using System.Diagnostics;
using System.Reflection;
using Microsoft.AutoGen.Contracts;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;

namespace Microsoft.AutoGen.Core;

public class AgentsAppBuilder
{
    private List<Func<AgentsApp, ValueTask<AgentType>>> AgentTypeRegistrations { get; } = new();

    private readonly HostApplicationBuilder builder;

    public AgentsAppBuilder(HostApplicationBuilder? baseBuilder = null)
    {
        this.builder = baseBuilder ?? new HostApplicationBuilder();
    }

    public IServiceCollection Services => this.builder.Services;

    public void AddAgentsFromAssemblies()
    {
        this.AddAgentsFromAssemblies(AppDomain.CurrentDomain.GetAssemblies());
    }

    public AgentsAppBuilder UseInProcessRuntime(bool deliverToSelf = false)
    {
        this.Services.AddSingleton<IAgentRuntime, InProcessRuntime>(_ => new InProcessRuntime { DeliverToSelf = deliverToSelf });
        this.Services.AddHostedService<InProcessRuntime>(services =>
        {
            return (services.GetRequiredService<IAgentRuntime>() as InProcessRuntime)!;
        });

        return this;
    }

    public AgentsAppBuilder AddAgentsFromAssemblies(params Assembly[] assemblies)
    {
        IEnumerable<Type> agentTypes = assemblies.SelectMany(assembly => assembly.GetTypes())
            .Where(type => ReflectionHelper.IsSubclassOfGeneric(type, typeof(BaseAgent))
                && !type.IsAbstract
                // && !type.Name.Equals(nameof(Client))
                );

        foreach (Type agentType in agentTypes)
        {
            // TODO: Expose skipClassSubscriptions and skipDirectMessageSubscription as parameters?
            this.AddAgent(agentType.Name, agentType);
        }

        return this;
    }

    private AgentsAppBuilder AddAgent(AgentType agentType, Type runtimeType, bool skipClassSubscriptions = false, bool skipDirectMessageSubscription = false)
    {
        this.AgentTypeRegistrations.Add(async app =>
        {
            await app.AgentRuntime.RegisterAgentTypeAsync(agentType, runtimeType, app.Services);
            await app.AgentRuntime.RegisterImplicitAgentSubscriptionsAsync(agentType, runtimeType, skipClassSubscriptions, skipDirectMessageSubscription);
            return agentType;
        });

        return this;
    }

    public AgentsAppBuilder AddAgent<TAgent>(AgentType agentType, bool skipClassSubscriptions = false, bool skipDirectMessageSubscription = false) where TAgent : IHostableAgent
        => this.AddAgent(agentType, typeof(TAgent), skipClassSubscriptions, skipDirectMessageSubscription);

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

    public IHostApplicationLifetime ApplicationLifetime => this.Services.GetRequiredService<IHostApplicationLifetime>();

    public IAgentRuntime AgentRuntime => this.Services.GetRequiredService<IAgentRuntime>();

    private int runningCount;
    public async ValueTask StartAsync()
    {
        if (Interlocked.Exchange(ref this.runningCount, 1) != 0)
        {
            throw new InvalidOperationException("Application is already running.");
        }

        Debug.Assert(this.AgentRuntime != null);

        await this.Host.StartAsync();
    }

    public async ValueTask ShutdownAsync()
    {
        if (Interlocked.Exchange(ref this.runningCount, 0) != 1)
        {
            throw new InvalidOperationException("Application is already stopped.");
        }

        await this.Host.StopAsync();
    }

    public async ValueTask PublishMessageAsync<TMessage>(TMessage message, TopicId topic, string? messageId = null, CancellationToken cancellationToken = default)
        where TMessage : notnull
    {
        if (Volatile.Read(ref this.runningCount) == 0)
        {
            await this.StartAsync();
        }

        await this.AgentRuntime.PublishMessageAsync(message, topic, messageId: messageId, cancellationToken: cancellationToken);
    }

    public Task WaitForShutdownAsync()
    {
        return this.Host.WaitForShutdownAsync();
    }
}
