// Copyright (c) Microsoft Corporation. All rights reserved.
// AgentProxy.cs

namespace Microsoft.AutoGen.Contracts.Python;

/// <summary>
/// A helper class that allows you to use an <see cref="AgentId"/> in place of its associated <see cref="IAgent"/>.
/// </summary>
public class AgentProxy(AgentId agentId, IAgentRuntime runtime)
{
    /// <summary>
    /// The runtime instance used to interact with agents.
    /// </summary>
    private IAgentRuntime runtime = runtime;

    /// <summary>
    /// The target agent for this proxy.
    /// </summary>
    public AgentId Id = agentId;

    private T ExecuteAndUnwrap<T>(Func<IAgentRuntime, ValueTask<T>> delegate_)
    {
        return delegate_(this.runtime).AsTask().ConfigureAwait(false).GetAwaiter().GetResult();
    }

    /// <summary>
    /// Gets the metadata of the agent.
    /// </summary>
    /// <value>
    /// An instance of <see cref="AgentMetadata"/> containing details about the agent.
    /// </value>
    public AgentMetadata Metadata => this.ExecuteAndUnwrap(runtime => runtime.GetAgentMetadataAsync(this.Id));

    // TODO: make this optional
    /// <summary>
    /// Sends a message to the agent and processes the response.
    /// </summary>
    /// <param name="message">The message to send to the agent.</param>
    /// <param name="sender">The agent that is sending the message.</param>
    /// <param name="messageId">
    /// The message ID. If <c>null</c>, a new message ID will be generated. 
    /// This message ID must be unique and is recommended to be a UUID.
    /// </param>
    /// <param name="cancellationToken">
    /// A token used to cancel an in-progress operation. Defaults to <c>null</c>.
    /// </param>
    /// <returns>A task representing the asynchronous operation, returning the response from the agent.</returns>
    public ValueTask<object> SendMessageAsync(object message, AgentId sender, string? messageId = null, CancellationToken? cancellationToken = default)
    {
        return this.runtime.SendMessageAsync(message, this.Id, sender, messageId, cancellationToken);
    }

    /// <summary>
    /// Loads the state of the agent from a previously saved state.
    /// </summary>
    /// <param name="state">A dictionary representing the state of the agent. Must be JSON serializable.</param>
    /// <returns>A task representing the asynchronous operation.</returns>
    public ValueTask LoadStateAsync(IDictionary<string, object> state)
    {
        return this.runtime.LoadAgentStateAsync(this.Id, state);
    }

    /// <summary>
    /// Saves the state of the agent. The result must be JSON serializable.
    /// </summary>
    /// <returns>A task representing the asynchronous operation, returning a dictionary containing the saved state.</returns>
    public ValueTask<IDictionary<string, object>> SaveStateAsync()
    {
        return this.runtime.SaveAgentStateAsync(this.Id);
    }
}
