
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
        ILogger<BaseAgent>? logger = null)
    {
        Id = id;
        _logger = logger ?? LoggerFactory.Create(builder => { }).CreateLogger<BaseAgent>();
        Description = description;
        Runtime = runtime;
        _handlersByMessageType = new(GetType().GetHandlersLookupTable());
    }

    public async ValueTask<object?> OnMessageAsync(object message, MessageContext messageContext)
    {
        // Determine type of message, then get handler method and invoke it
        var messageType = message.GetType();
        if (_handlersByMessageType.TryGetValue(messageType, out var handlerMethod))
        {
            // Determine if this is a IHandle<T> or IHandle<T, U> method
            var genericArguments = handlerMethod.GetParameters();
            if (genericArguments.Length == 1)
            {
                // This is a IHandle<T> method
                var return_value = handlerMethod.Invoke(this, new object[] { message, messageContext });
                if (return_value != null){
                    await (ValueTask)return_value;
                }
                return ValueTask.CompletedTask;

            }
            else if (genericArguments.Length == 2)
            {
                // This is a IHandle<T, U> method
                // var _messageType = genericArguments[0];
                // var _returnType = genericArguments[1];
                var result = handlerMethod.Invoke(this, new object[] { message, messageContext });
                if (result != null){
                    return await (ValueTask<object?>)result;
                }

                throw new InvalidOperationException($"Got null result from handler method {handlerMethod.Name}");
            }
            else
            {
                throw new InvalidOperationException($"Unexpected number of generic arguments in handler method {handlerMethod.Name}");
            }
        }
        else
        {
            throw new InvalidOperationException($"No handler found for message type {messageType.FullName}");
        }
    }

    public virtual ValueTask<IDictionary<string, object>> SaveStateAsync()
    {
        return ValueTask.FromResult<IDictionary<string, object>>(new Dictionary<string, object>());
    }
    public virtual ValueTask LoadStateAsync(IDictionary<string, object> state)
    {
        return ValueTask.CompletedTask;
    }

    public ValueTask<object?> SendMessageAsync(object message, AgentId recepient, string? messageId = null, CancellationToken? cancellationToken = default)
    {
        return this.Runtime.SendMessageAsync(message, recepient, sender: this.Id, messageId: messageId, cancellationToken: cancellationToken);

    }

    public ValueTask PublishMessageAsync(object message, TopicId topic, string? messageId = null, CancellationToken? cancellationToken = default)
    {
        return this.Runtime.PublishMessageAsync(message, topic, sender: this.Id, messageId: messageId, cancellationToken: cancellationToken);
    }
}
