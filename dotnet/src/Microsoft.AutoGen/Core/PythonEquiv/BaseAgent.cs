
// Copyright (c) Microsoft Corporation. All rights reserved.
// Agent.cs

using System.Diagnostics;
using System.Reflection;
using Microsoft.AutoGen.Contracts.Python;
using Microsoft.Extensions.Logging;

namespace Microsoft.AutoGen.Core.Python;
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
    protected internal ILogger<Agent> _logger;

    public Type[] HandledTypes {
        get {
            return _handlersByMessageType.Keys.ToArray();
        }
    }

    protected IUnboundSubscriptionDefinition[] GetUnboundSubscriptions()
    {
        throw new NotImplementedException();
    }

    protected IAgentRuntime Runtime { get; private set; }
    private readonly Dictionary<Type, MethodInfo> _handlersByMessageType;

    protected string Description { get; private set; }

    public AgentMetadata Metadata {
        get {
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
        ILogger<Agent>? logger = null)
    {
        Id = id;
        _logger = logger ?? LoggerFactory.Create(builder => { }).CreateLogger<Agent>();
        Description = description;
        Runtime = runtime;
        _handlersByMessageType = new(GetType().GetHandlersLookupTable());
    }

    public ISubscriptionDefinition[] BindSubscriptionsForAgentType(AgentType agentType, bool skipClassSubscriptions = false, bool skipDirectMessageSubscription = false)
    {
        // var topicAttributes = this.GetType().GetCustomAttributes<TopicSubscriptionAttribute>().Select(t => t.Topic);
        var subscriptions = new List<ISubscriptionDefinition>();

        if (!skipClassSubscriptions)
        {
            var classSubscriptions = this.GetType().GetCustomAttributes<TypeSubscriptionAttribute>().Select(t => t.Bind(agentType));
            subscriptions.AddRange(classSubscriptions);

            var prefixSubscriptions = this.GetType().GetCustomAttributes<TopicPrefixSubscriptionAttribute>().Select(t => t.Bind(agentType));
            subscriptions.AddRange(prefixSubscriptions);
        }

        if (!skipDirectMessageSubscription)
        {
            subscriptions.Add(new TypePrefixSubscription(agentType.Name + ":", agentType));
        }

        return subscriptions.ToArray();
    }

    public ValueTask<object?> OnMessageAsync(object message, MessageContext messageContext)
    {
        // Determine type of message, then get handler method and invoke it
        var messageType = message.GetType();
        if (_handlersByMessageType.TryGetValue(messageType, out var handlerMethod))
        {
            // Determine if this is a IHandle<T> or IHandle<T, U> method
            var genericArguments = handlerMethod.GetGenericArguments();
            if (genericArguments.Length == 1)
            {
                // This is a IHandle<T> method
                var return_value = handlerMethod.Invoke(this, new object[] { message, messageContext });
                return ValueTask.FromResult(return_value);

            }
            else if (genericArguments.Length == 2)
            {
                // This is a IHandle<T, U> method
                // var _messageType = genericArguments[0];
                // var _returnType = genericArguments[1];
                var result = handlerMethod.Invoke(this, new object[] { message, messageContext });

                return ValueTask.FromResult(result);
            }
            else
            {
                return ValueTask.FromException<object?>(new InvalidOperationException($"Unexpected number of generic arguments in handler method {handlerMethod.Name}"));
            }
        }
        else
        {
            return ValueTask.FromException<object?>(new InvalidOperationException($"No handler found for message type {messageType.FullName}"));
        }
    }

    public ValueTask<IDictionary<string, object>> SaveStateAsync()
    {
        // Raise not implemented exception
        throw new NotImplementedException();
    }
    public ValueTask LoadStateAsync(IDictionary<string, object> state)
    {
        // Raise not implemented exception
        throw new NotImplementedException();
    }

    public ValueTask<object> SendMessageAsync(object message, AgentId recepient, string? messageId = null, CancellationToken? cancellationToken = default)
    {
        return this.Runtime.SendMessageAsync(message, recepient, sender: this.Id, messageId: messageId, cancellationToken: cancellationToken);

    }

    public ValueTask<object> PublishMessageAsync(object message, TopicId topic, string? messageId = null, CancellationToken? cancellationToken = default)
    {
        return this.Runtime.PublishMessageAsync(message, topic, sender: this.Id, messageId: messageId, cancellationToken: cancellationToken);
    }
}
