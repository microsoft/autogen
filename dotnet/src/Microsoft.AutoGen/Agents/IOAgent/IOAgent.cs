// Copyright (c) Microsoft Corporation. All rights reserved.
// IOAgent.cs
using Microsoft.AutoGen.Contracts;
using Microsoft.AutoGen.Core;
using Microsoft.Extensions.Logging;

namespace Microsoft.AutoGen.Agents;
public abstract class IOAgent : BaseAgent, IProcessIO
{
    private readonly TopicId _topicId;
    private static string MessageId => Guid.NewGuid().ToString();
    protected IOAgent(
        AgentId id,
        IAgentRuntime runtime,
        string name,
        ILogger<IOAgent> logger) : base(
            id,
            runtime,
            name,
            logger)
    {
        _topicId = new TopicId(GetType().FullName ?? "Microsoft.AutoGen.Agents.IOAgent");
    }
    public virtual async Task HandleAsync(Input item, CancellationToken cancellationToken)
    {

        var evt = new InputProcessed
        {
            Route = _topicId.Type
        };
        await PublishMessageAsync(evt, _topicId, MessageId, cancellationToken);
    }

    public virtual async Task HandleAsync(Output item, CancellationToken cancellationToken)
    {
        var evt = new OutputWritten
        {
            Route = _topicId.Type
        };
        await PublishMessageAsync(evt, _topicId, MessageId, cancellationToken);
    }
}
