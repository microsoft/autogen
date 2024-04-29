// Copyright (c) Microsoft Corporation. All rights reserved.
// StreamingMiddlewareExtension.cs

using System;
using System.Collections.Generic;
using System.Threading;
using System.Threading.Tasks;

namespace AutoGen.Core;

public static class StreamingMiddlewareExtension
{
    /// <summary>
    /// Register a middleware to an existing agent and return a new agent with the middleware.
    /// </summary>
    public static MiddlewareStreamingAgent<TStreamingAgent> RegisterStreamingMiddleware<TStreamingAgent>(
        this TStreamingAgent agent,
        IStreamingMiddleware middleware)
        where TStreamingAgent : IStreamingAgent
    {
        var middlewareAgent = new MiddlewareStreamingAgent<TStreamingAgent>(agent);
        middlewareAgent.UseStreaming(middleware);

        if (middleware is IMiddleware middlewareBase)
        {
            middlewareAgent.Use(middlewareBase);
        }

        return middlewareAgent;
    }

    /// <summary>
    /// Register a middleware to an existing agent and return a new agent with the middleware.
    /// </summary>
    public static MiddlewareStreamingAgent<TAgent> RegisterStreamingMiddleware<TAgent>(
        this MiddlewareStreamingAgent<TAgent> agent,
        IStreamingMiddleware middleware)
        where TAgent : IStreamingAgent
    {
        var copyAgent = new MiddlewareStreamingAgent<TAgent>(agent);
        copyAgent.UseStreaming(middleware);

        if (middleware is IMiddleware middlewareBase)
        {
            copyAgent.Use(middlewareBase);
        }

        return copyAgent;
    }


    /// <summary>
    /// Register a middleware to an existing agent and return a new agent with the middleware.
    /// </summary>
    public static MiddlewareStreamingAgent<TAgent> RegisterStreamingMiddleware<TAgent>(
        this TAgent agent,
        Func<MiddlewareContext, IStreamingAgent, CancellationToken, Task<IAsyncEnumerable<IStreamingMessage>>> func,
        string? middlewareName = null)
        where TAgent : IStreamingAgent
    {
        var middleware = new DelegateStreamingMiddleware(middlewareName, new DelegateStreamingMiddleware.MiddlewareDelegate(func));

        return agent.RegisterStreamingMiddleware(middleware);
    }

    /// <summary>
    /// Register a streaming middleware to an existing agent and return a new agent with the middleware.
    /// </summary>
    public static MiddlewareStreamingAgent<TAgent> RegisterStreamingMiddleware<TAgent>(
        this MiddlewareStreamingAgent<TAgent> agent,
        Func<MiddlewareContext, IStreamingAgent, CancellationToken, Task<IAsyncEnumerable<IStreamingMessage>>> func,
        string? middlewareName = null)
        where TAgent : IStreamingAgent
    {
        var middleware = new DelegateStreamingMiddleware(middlewareName, new DelegateStreamingMiddleware.MiddlewareDelegate(func));

        return agent.RegisterStreamingMiddleware(middleware);
    }

    /// <summary>
    /// Register a middleware to an existing streaming agent and return a new agent with the middleware.
    /// </summary>
    public static MiddlewareStreamingAgent<TStreamingAgent> RegisterMiddleware<TStreamingAgent>(
        this MiddlewareStreamingAgent<TStreamingAgent> streamingAgent,
        Func<IEnumerable<IMessage>, GenerateReplyOptions?, IAgent, CancellationToken, Task<IMessage>> func,
        string? middlewareName = null)
        where TStreamingAgent : IStreamingAgent
    {
        var middleware = new DelegateMiddleware(middlewareName, async (context, agent, cancellationToken) =>
        {
            return await func(context.Messages, context.Options, agent, cancellationToken);
        });

        return streamingAgent.RegisterMiddleware(middleware);
    }

    /// <summary>
    /// Register a middleware to an existing streaming agent and return a new agent with the middleware.
    /// </summary>
    public static MiddlewareStreamingAgent<TStreamingAgent> RegisterMiddleware<TStreamingAgent>(
        this MiddlewareStreamingAgent<TStreamingAgent> streamingAgent,
        IMiddleware middleware)
        where TStreamingAgent : IStreamingAgent
    {
        var copyAgent = new MiddlewareStreamingAgent<TStreamingAgent>(streamingAgent);
        copyAgent.Use(middleware);
        if (middleware is IStreamingMiddleware streamingMiddleware)
        {
            copyAgent.UseStreaming(streamingMiddleware);
        }

        return copyAgent;
    }
}
