// Copyright (c) Microsoft Corporation. All rights reserved.
// MiddlewareStreamingAgent.cs

using System;
using System.Collections.Generic;
using System.Threading;
using System.Threading.Tasks;
using AutoGen.Core.Middleware;

namespace AutoGen;

public class MiddlewareStreamingAgent : IStreamingAgent
{
    private readonly IStreamingAgent _agent;
    private readonly List<IStreamingMiddleware> _middlewares = new();

    public MiddlewareStreamingAgent(IStreamingAgent agent, string? name = null, IEnumerable<IStreamingMiddleware>? middlewares = null)
    {
        _agent = agent;
        Name = name ?? agent.Name;
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
    /// Get the middlewares.
    /// </summary>
    public IEnumerable<IStreamingMiddleware> Middlewares => _middlewares;

    public async Task<Message> GenerateReplyAsync(IEnumerable<Message> messages, GenerateReplyOptions? options = null, CancellationToken cancellationToken = default)
    {
        throw new NotImplementedException("Streaming agent does not support non-streaming reply.");
    }

    public Task<IAsyncEnumerable<IMessage>> GenerateStreamingReplyAsync(IEnumerable<IMessage> messages, GenerateReplyOptions? options = null, CancellationToken cancellationToken = default)
    {
        var agent = _agent;
        foreach (var middleware in _middlewares)
        {
            agent = new DelegateStreamingAgent(middleware, agent);
        }

        return agent.GenerateStreamingReplyAsync(messages, options, cancellationToken);
    }

    public void Use(IStreamingMiddleware middleware)
    {
        _middlewares.Add(middleware);
    }

    public void Use(Func<MiddlewareContext, IStreamingAgent, CancellationToken, Task<IAsyncEnumerable<IMessage>>> func, string? middlewareName = null)
    {
        _middlewares.Add(new DelegateStreamingMiddleware(middlewareName, new DelegateStreamingMiddleware.MiddlewareDelegate(func)));
    }

    private class DelegateStreamingAgent : IStreamingAgent
    {
        private IStreamingMiddleware middleware;
        private IStreamingAgent innerAgent;

        public string Name => innerAgent.Name;

        public DelegateStreamingAgent(IStreamingMiddleware middleware, IStreamingAgent next)
        {
            this.middleware = middleware;
            this.innerAgent = next;
        }

        public async Task<Message> GenerateReplyAsync(IEnumerable<Message> messages, GenerateReplyOptions? options = null, CancellationToken cancellationToken = default)
        {
            throw new NotImplementedException("Streaming agent does not support non-streaming reply.");
        }

        public Task<IAsyncEnumerable<IMessage>> GenerateStreamingReplyAsync(IEnumerable<IMessage> messages, GenerateReplyOptions? options = null, CancellationToken cancellationToken = default)
        {
            // TODO
            // fix this
            var context = new MiddlewareContext((IEnumerable<Message>)messages, options);
            return middleware.InvokeAsync(context, innerAgent, cancellationToken);
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
