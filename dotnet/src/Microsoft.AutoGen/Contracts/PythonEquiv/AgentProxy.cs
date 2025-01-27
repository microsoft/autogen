// Copyright (c) Microsoft Corporation. All rights reserved.
// AgentProxy.cs


namespace Microsoft.AutoGen.Contracts.Python;

public class AgentProxy(AgentId agentId, IAgentRuntime runtime)
{
    private IAgentRuntime runtime = runtime;
    public AgentId Id = agentId;

    private T ExecuteAndUnwrap<T>(Func<IAgentRuntime, ValueTask<T>> delegate_)
    {
        return delegate_(this.runtime).AsTask().ConfigureAwait(false).GetAwaiter().GetResult();
    }

    public AgentMetadata Metadata => this.ExecuteAndUnwrap(runtime => runtime.GetAgentMetadataAsync(this.Id));

    // TODO: make this optional
    public ValueTask<object> SendMessageAsync(object message, AgentId sender, string? messageId = null, CancellationToken? cancellationToken = default)
    {
        return this.runtime.SendMessageAsync(message, this.Id, sender, messageId, cancellationToken);
    }

    public ValueTask LoadStateAsync(IDictionary<string, object> state)
    {
        return this.runtime.LoadAgentStateAsync(state);
    }

    public ValueTask<IDictionary<string, object>> SaveStateAsync()
    {
        return this.runtime.SaveAgentStateAsync();
    }
}
