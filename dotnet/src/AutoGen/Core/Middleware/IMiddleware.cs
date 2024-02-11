// Copyright (c) Microsoft Corporation. All rights reserved.
// IMiddleware.cs

using System;
using System.Collections.Generic;
using System.Threading;
using System.Threading.Tasks;

namespace AutoGen.Core.Middleware;

/// <summary>
/// The middleware interface
/// </summary>
public interface IMiddleware
{
    /// <summary>
    /// the name of the middleware
    /// </summary>
    public string? Name { get; }

    /// <summary>
    /// The method to invoke the middleware
    /// </summary>
    public Task<Message> InvokeAsync(
        MiddlewareContext context,
        IAgent agent,
        CancellationToken cancellationToken = default);
}

/// <summary>
/// The streaming middleware interface
/// </summary>
public interface IStreamingMiddleware
{
    public string? Name { get; }

    public Task<IAsyncEnumerable<Message>> InvokeAsync(
        MiddlewareContext context,
        IStreamingAgent agent,
        CancellationToken cancellationToken = default);
}

public class MiddlewareContext
{
    public MiddlewareContext(
        IEnumerable<Message> messages,
        GenerateReplyOptions? options)
    {
        this.Messages = messages;
        this.Options = options;
    }

    /// <summary>
    /// Messages to send to the agent
    /// </summary>
    public IEnumerable<Message> Messages { get; }

    /// <summary>
    /// Options to generate the reply
    /// </summary>
    public GenerateReplyOptions? Options { get; }
}

internal class DelegateMiddleware : IMiddleware
{
    /// <summary>
    /// middleware delegate. Call into the next function to continue the execution of the next middleware. Otherwise, short cut the middleware execution.
    /// </summary>
    /// <param name="cancellationToken">cancellation token</param>
    public delegate Task<Message> MiddlewareDelegate(
        MiddlewareContext context,
        IAgent agent,
        CancellationToken cancellationToken);

    private readonly MiddlewareDelegate middlewareDelegate;

    public DelegateMiddleware(string? name, Func<MiddlewareContext, IAgent, CancellationToken, Task<Message>> middlewareDelegate)
    {
        this.Name = name;
        this.middlewareDelegate = async (context, agent, cancellationToken) =>
        {
            return await middlewareDelegate(context, agent, cancellationToken);
        };
    }

    public string? Name { get; }

    public Task<Message> InvokeAsync(
        MiddlewareContext context,
        IAgent agent,
        CancellationToken cancellationToken = default)
    {
        var messages = context.Messages;
        var options = context.Options;

        return this.middlewareDelegate(context, agent, cancellationToken);
    }
}

internal class DelegateStreamingMiddleware : IStreamingMiddleware
{
    public delegate Task<IAsyncEnumerable<Message>> MiddlewareDelegate(
        MiddlewareContext context,
        IStreamingAgent agent,
        CancellationToken cancellationToken);

    private readonly MiddlewareDelegate middlewareDelegate;

    public DelegateStreamingMiddleware(string? name, MiddlewareDelegate middlewareDelegate)
    {
        this.Name = name;
        this.middlewareDelegate = middlewareDelegate;
    }

    public string? Name { get; }

    public Task<IAsyncEnumerable<Message>> InvokeAsync(
               MiddlewareContext context,
               IStreamingAgent agent,
               CancellationToken cancellationToken = default)
    {
        var messages = context.Messages;
        var options = context.Options;

        return this.middlewareDelegate(context, agent, cancellationToken);
    }
}
