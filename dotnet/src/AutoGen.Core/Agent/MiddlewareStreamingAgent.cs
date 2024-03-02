// Copyright (c) Microsoft Corporation. All rights reserved.
// MiddlewareStreamingAgent.cs

using System;
using System.Collections.Generic;
using System.Threading;
using System.Threading.Tasks;

namespace AutoGen.Core;

public class MiddlewareStreamingAgent : IStreamingAgent
{
    private readonly IStreamingAgent _agent;
    private readonly List<IStreamingMiddleware> _streamingMiddlewares = new();
    private readonly List<IMiddleware> _middlewares = new();

    public MiddlewareStreamingAgent(
        IStreamingAgent agent,
        string? name = null,
        IEnumerable<IStreamingMiddleware>? streamingMiddlewares = null,
        IEnumerable<IMiddleware>? middlewares = null)
    {
        _agent = agent;
        Name = name ?? agent.Name;
        if (streamingMiddlewares != null)
        {
            _streamingMiddlewares.AddRange(streamingMiddlewares);
        }

        if (middlewares != null)
        {
            _middlewares.AddRange(middlewares);
        }
    }

    public string Name { get; }

    /// <summary>
    /// Get the inner agent.
    /// </summary>
    public IStreamingAgent Agent => _agent;

    /// <summary>
    /// Get the streaming middlewares.
    /// </summary>
    public IEnumerable<IStreamingMiddleware> StreamingMiddlewares => _streamingMiddlewares;

    /// <summary>
    /// Get the middlewares.
    /// </summary>
    public IEnumerable<IMiddleware> Middlewares => _middlewares;

    public async Task<IMessage> GenerateReplyAsync(IEnumerable<IMessage> messages, GenerateReplyOptions? options = null, CancellationToken cancellationToken = default)
    {
        var agent = _agent;
        foreach (var middleware in _middlewares)
        {
            agent = new DelegateStreamingAgent(middleware, agent);
        }

        return await agent.GenerateReplyAsync(messages, options, cancellationToken);
    }

    public Task<IAsyncEnumerable<IStreamingMessage>> GenerateStreamingReplyAsync(IEnumerable<IMessage> messages, GenerateReplyOptions? options = null, CancellationToken cancellationToken = default)
    {
        var agent = _agent;
        foreach (var middleware in _streamingMiddlewares)
        {
            agent = new DelegateStreamingAgent(middleware, agent);
        }

        return agent.GenerateStreamingReplyAsync(messages, options, cancellationToken);
    }

    public void UseStreaming(IStreamingMiddleware middleware)
    {
        _streamingMiddlewares.Add(middleware);
    }

    public void UseStreaming(Func<MiddlewareContext, IStreamingAgent, CancellationToken, Task<IAsyncEnumerable<IStreamingMessage>>> func, string? middlewareName = null)
    {
        _streamingMiddlewares.Add(new DelegateStreamingMiddleware(middlewareName, new DelegateStreamingMiddleware.MiddlewareDelegate(func)));
    }

    public void Use(IMiddleware middleware)
    {
        _middlewares.Add(middleware);
    }

    public void Use(Func<IEnumerable<IMessage>, GenerateReplyOptions?, IAgent, CancellationToken, Task<IMessage>> func, string? middlewareName = null)
    {
        _middlewares.Add(new DelegateMiddleware(middlewareName, async (context, agent, cancellationToken) =>
        {
            return await func(context.Messages, context.Options, agent, cancellationToken);
        }));
    }

    private class DelegateStreamingAgent : IStreamingAgent
    {
        private IStreamingMiddleware? streamingMiddleware;
        private IMiddleware? middleware;
        private IStreamingAgent innerAgent;

        public string Name => innerAgent.Name;

        public DelegateStreamingAgent(IStreamingMiddleware middleware, IStreamingAgent next)
        {
            this.streamingMiddleware = middleware;
            this.innerAgent = next;
        }

        public DelegateStreamingAgent(IMiddleware middleware, IStreamingAgent next)
        {
            this.middleware = middleware;
            this.innerAgent = next;
        }

        public async Task<IMessage> GenerateReplyAsync(IEnumerable<IMessage> messages, GenerateReplyOptions? options = null, CancellationToken cancellationToken = default)
        {
            if (middleware is null)
            {
                return await innerAgent.GenerateReplyAsync(messages, options, cancellationToken);
            }

            var context = new MiddlewareContext(messages, options);
            return await middleware.InvokeAsync(context, innerAgent, cancellationToken);
        }

        public Task<IAsyncEnumerable<IStreamingMessage>> GenerateStreamingReplyAsync(IEnumerable<IMessage> messages, GenerateReplyOptions? options = null, CancellationToken cancellationToken = default)
        {
            if (streamingMiddleware is null)
            {
                return innerAgent.GenerateStreamingReplyAsync(messages, options, cancellationToken);
            }

            var context = new MiddlewareContext(messages, options);
            return streamingMiddleware.InvokeAsync(context, innerAgent, cancellationToken);
        }
    }
}

public sealed class MiddlewareStreamingAgent<T> : MiddlewareStreamingAgent
    where T : IStreamingAgent
{
    public MiddlewareStreamingAgent(T innerAgent, string? name = null)
        : base(innerAgent, name)
    {
        TAgent = innerAgent;
    }

    public MiddlewareStreamingAgent(MiddlewareStreamingAgent<T> other)
        : base(other)
    {
        TAgent = other.TAgent;
    }

    /// <summary>
    /// Get the inner agent.
    /// </summary>
    public T TAgent { get; }
}
