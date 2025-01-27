// Copyright (c) Microsoft Corporation. All rights reserved.
// IAgent.cs

namespace Microsoft.AutoGen.Contracts.Python;

public interface IAgent : ISaveState<IAgent>
{
    public AgentId Id { get; }
    public AgentMetadata Metadata { get; }

    public ValueTask<object> OnMessageAsync(object message, MessageContext messageContext); // TODO: How do we express this properly in .NET?
}

public interface IHostableAgent : IAgent
{
    public ValueTask CloseAsync();
}

