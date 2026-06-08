// Copyright (c) Microsoft Corporation. All rights reserved.
// MiddlewareContext.cs

using System.Collections.Generic;

namespace AutoGen.Core;

public class MiddlewareContext
{
    public MiddlewareContext(
        IEnumerable<IMessage> messages,
        GenerateReplyOptions? options)
    {
        this.Messages = messages;
        this.Options = options;
    }

    /// <summary>
    /// Messages to send to the agent
    /// </summary>
    public IEnumerable<IMessage> Messages { get; }

    /// <summary>
    /// Options to generate the reply
    /// </summary>
    public GenerateReplyOptions? Options { get; }
}
