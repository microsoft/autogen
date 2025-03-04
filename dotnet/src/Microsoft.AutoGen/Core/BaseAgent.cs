
// Copyright (c) Microsoft Corporation. All rights reserved.
// BaseAgent.cs

using System.Diagnostics;
using System.Reflection;
using Microsoft.AutoGen.Contracts;
using Microsoft.Extensions.Logging;

namespace Microsoft.AutoGen.Core;

/// <summary>
/// Represents the base class for an agent in the AutoGen system.
/// </summary>
public abstract class BaseAgent : IAgent, IHostableAgent
{
    /// <summary>
    /// The activity source for tracing.
    /// </summary>
    public static readonly ActivitySource s_source = new("Microsoft.AutoGen.Core.Agent");

    /// <summary>
    /// Gets the unique identifier of the agent.
    /// </summary>
    public AgentId Id { get; private set; }
    protected internal ILogger<BaseAgent> _logger;

    protected IAgentRuntime Runtime { get; private set; }
    private readonly Dictionary<Type, HandlerInvoker> handlerInvokers;

    protected string Description { get; private set; }

    public AgentMetadata Metadata
    {
        get
        {
            return new AgentMetadata
            {
                Type = Id.Type,
                Key = Id.Key,
                Description = Description
            };
        }
    }

    protected BaseAgent(
        AgentId id,
        IAgentRuntime runtime,
        string description,
        ILogger<BaseAgent>? logger = null)
    {
        Id = id;
        _logger = logger ?? LoggerFactory.Create(builder => { }).CreateLogger<BaseAgent>();
        Description = description;
        Runtime = runtime;

        this.handlerInvokers = this.ReflectInvokers();
    }

    private Dictionary<Type, HandlerInvoker> ReflectInvokers()
    {
        Type realType = this.GetType();

        IEnumerable<Type> candidateInterfaces =
            realType.GetInterfaces()
                    .Where(i => i.IsGenericType &&
                            (i.GetGenericTypeDefinition() == typeof(IHandle<>) ||
                            (i.GetGenericTypeDefinition() == typeof(IHandle<,>))));

        Dictionary<Type, HandlerInvoker> invokers = new();
        foreach (Type interface_ in candidateInterfaces)
        {
            MethodInfo handleAsync = interface_.GetMethod(nameof(IHandle<object>.HandleAsync), BindingFlags.Instance | BindingFlags.Public)
                                     ?? throw new InvalidOperationException($"No handler method found for interface {interface_.FullName}");

            HandlerInvoker invoker = new(handleAsync, this);
            invokers.Add(interface_.GetGenericArguments()[0], invoker);
        }

        return invokers;
    }

    public async ValueTask<object?> OnMessageAsync(object message, MessageContext messageContext)
    {
        // Determine type of message, then get handler method and invoke it
        var messageType = message.GetType();
        if (this.handlerInvokers.TryGetValue(messageType, out var handlerInvoker))
        {
            return await handlerInvoker.InvokeAsync(message, messageContext);
        }

        return null;
    }

    public ValueTask<object?> SendMessageAsync(object message, AgentId recepient, string? messageId = null, CancellationToken cancellationToken = default)
    {
        return this.Runtime.SendMessageAsync(message, recepient, sender: this.Id, messageId: messageId, cancellationToken: cancellationToken);

    }

    public ValueTask PublishMessageAsync(object message, TopicId topic, string? messageId = null, CancellationToken cancellationToken = default)
    {
        return this.Runtime.PublishMessageAsync(message, topic, sender: this.Id, messageId: messageId, cancellationToken: cancellationToken);
    }
}
