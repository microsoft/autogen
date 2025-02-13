// Copyright (c) Microsoft Corporation. All rights reserved.
// IAgent.cs

namespace Microsoft.AutoGen.Contracts;

/// <summary>
/// Represents an agent within the runtime that can process messages, maintain state, and be closed when no longer needed.
/// </summary>
public interface IAgent : ISaveState
{
    /// <summary>
    /// Gets the unique identifier of the agent.
    /// </summary>
    public AgentId Id { get; }

    /// <summary>
    /// Gets metadata associated with the agent.
    /// </summary>
    public AgentMetadata Metadata { get; }

    /// <summary>
    /// Handles an incoming message for the agent.
    /// This should only be called by the runtime, not by other agents.
    /// </summary>
    /// <param name="message">The received message. The type should match one of the expected subscription types.</param>
    /// <param name="messageContext">The context of the message, providing additional metadata.</param>
    /// <returns>
    /// A task representing the asynchronous operation, returning a response to the message.
    /// The response can be <c>null</c> if no reply is necessary.
    /// </returns>
    /// <exception cref="OperationCanceledException">Thrown if the message was cancelled.</exception>
    /// <exception cref="CantHandleException">Thrown if the agent cannot handle the message.</exception>
    public ValueTask<object?> OnMessageAsync(object message, MessageContext messageContext); // TODO: How do we express this properly in .NET?
}

/// <summary>
/// Represents an agent that can be explicitly hosted and closed when the runtime shuts down.
/// </summary>
public interface IHostableAgent : IAgent
{
    /// <summary>
    /// Called when the runtime is closing.
    /// </summary>
    /// <returns>A task representing the asynchronous operation.</returns>
    public ValueTask CloseAsync() => ValueTask.CompletedTask;
}

