// Copyright (c) Microsoft Corporation. All rights reserved.
// DelegateMiddleware.cs

using System;
using System.Threading;
using System.Threading.Tasks;

namespace AutoGen.Core;

internal sealed class DelegateMiddleware : IMiddleware
{
    /// <summary>
    /// middleware delegate. Call into the next function to continue the execution of the next middleware. Otherwise, short cut the middleware execution.
    /// </summary>
    /// <param name="cancellationToken">cancellation token</param>
    public delegate Task<IMessage> MiddlewareDelegate(
        MiddlewareContext context,
        IAgent agent,
        CancellationToken cancellationToken);

    private readonly MiddlewareDelegate middlewareDelegate;

    public DelegateMiddleware(string? name, Func<MiddlewareContext, IAgent, CancellationToken, Task<IMessage>> middlewareDelegate)
    {
        this.Name = name;
        this.middlewareDelegate = async (context, agent, cancellationToken) =>
        {
            return await middlewareDelegate(context, agent, cancellationToken);
        };
    }

    public string? Name { get; }

    public Task<IMessage> InvokeAsync(
        MiddlewareContext context,
        IAgent agent,
        CancellationToken cancellationToken = default)
    {
        var messages = context.Messages;
        var options = context.Options;

        return this.middlewareDelegate(context, agent, cancellationToken);
    }
}

