// Copyright (c) Microsoft Corporation. All rights reserved.
// AgentsApp.cs

using Microsoft.AutoGen.Contracts;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using System.Reflection;

namespace Microsoft.AutoGen.Core;

public class AgentsAppBuilder
{
    private List<Func<AgentsApp, ValueTask<AgentType>>> AgentTypeRegistrations { get; } = new();

    private readonly HostApplicationBuilder builder;

    public AgentsAppBuilder(HostApplicationBuilder? baseBuilder = null)
    {
        this.builder = baseBuilder ?? new HostApplicationBuilder();
    }

    public void AddAgentsFromAssemblies()
    {
        this.AddAgentsFromAssemblies(AppDomain.CurrentDomain.GetAssemblies());
    }

    public void AddAgentsFromAssemblies(params Assembly[] assemblies)
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
    }

    private void AddAgent(AgentType agentType, Type runtimeType, bool skipClassSubscriptions = false, bool skipDirectMessageSubscription = false)
    {
        this.AgentTypeRegistrations.Add(async app =>
        {
            await app.AgentRuntime.RegisterAgentTypeAsync(agentType, runtimeType, app.Services);
            await app.AgentRuntime.RegisterImplicitAgentSubscriptionsAsync(agentType, runtimeType, skipClassSubscriptions, skipDirectMessageSubscription);
            return agentType;
        });
    }

    public void AddAgent<TAgent>(AgentType agentType, bool skipClassSubscriptions = false, bool skipDirectMessageSubscription = false) where TAgent : IHostableAgent
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
