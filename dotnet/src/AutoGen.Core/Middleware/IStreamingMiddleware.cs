// Copyright (c) Microsoft Corporation. All rights reserved.
// IStreamingMiddleware.cs

using System.Collections.Generic;
using System.Threading;

namespace AutoGen.Core;

/// <summary>
/// The streaming middleware interface. For non-streaming version middleware, check <see cref="IMiddleware"/>.
/// </summary>
public interface IStreamingMiddleware : IMiddleware
{
    /// <summary>
    /// The streaming version of <see cref="IMiddleware.InvokeAsync(MiddlewareContext, IAgent, CancellationToken)"/>.
    /// </summary>
    public IAsyncEnumerable<IMessage> InvokeAsync(
        MiddlewareContext context,
        IStreamingAgent agent,
        CancellationToken cancellationToken = default);
}
