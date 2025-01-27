// Copyright (c) Microsoft Corporation. All rights reserved.
// AgentProxy.cs


namespace Microsoft.AutoGen.Contracts.Python;

public class AgentProxy(AgentId agentId, IAgentRuntime runtime) //: IAgent
{
    private IAgentRuntime runtime = runtime;
    public AgentId Id = agentId;

    private T ExecuteAndUnwrap<T>(Func<IAgentRuntime, ValueTask<T>> delegate_)
    {
        return delegate_(this.runtime).AsTask().ConfigureAwait(false).GetAwaiter().GetResult();
    }

    public AgentMetadata Metadata => this.ExecuteAndUnwrap(runtime => runtime.GetAgentMetadataAsync(this.Id));

    public ValueTask LoadStateAsync(IDictionary<string, object> state)
    {
        throw new NotImplementedException();
    }

    public ValueTask<object> OnMessageAsync(object message, MessageContext messageContext)
    {
        throw new NotImplementedException();
    }

    public ValueTask<IDictionary<string, object>> SaveStateAsync()
    {
        throw new NotImplementedException();
    }
}
