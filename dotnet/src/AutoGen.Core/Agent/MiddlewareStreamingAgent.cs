// Copyright (c) Microsoft Corporation. All rights reserved.
// MiddlewareStreamingAgent.cs

using System.Collections.Generic;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;

namespace AutoGen.Core;

public class MiddlewareStreamingAgent : IMiddlewareStreamAgent
{
    private IStreamingAgent _agent;
    private readonly List<IStreamingMiddleware> _streamingMiddlewares = new();

    public MiddlewareStreamingAgent(
        IStreamingAgent agent,
        string? name = null,
        IEnumerable<IStreamingMiddleware>? streamingMiddlewares = null)
    {
        this.Name = name ?? agent.Name;
        _agent = agent;

        if (streamingMiddlewares != null && streamingMiddlewares.Any())
        {
            foreach (var middleware in streamingMiddlewares)
            {
                this.UseStreaming(middleware);
            }
        }
    }

    /// <summary>
    /// Get the inner agent.
    /// </summary>
    public IStreamingAgent StreamingAgent => _agent;

    /// <summary>
    /// Get the streaming middlewares.
    /// </summary>
    public IEnumerable<IStreamingMiddleware> StreamingMiddlewares => _streamingMiddlewares;

    public string Name { get; }

    public Task<IMessage> GenerateReplyAsync(IEnumerable<IMessage> messages, GenerateReplyOptions? options = null, CancellationToken cancellationToken = default)
    {
        return _agent.GenerateReplyAsync(messages, options, cancellationToken);
    }

    public IAsyncEnumerable<IMessage> GenerateStreamingReplyAsync(IEnumerable<IMessage> messages, GenerateReplyOptions? options = null, CancellationToken cancellationToken = default)
    {
        return _agent.GenerateStreamingReplyAsync(messages, options, cancellationToken);
    }

    public void UseStreaming(IStreamingMiddleware middleware)
    {
        _streamingMiddlewares.Add(middleware);
        _agent = new DelegateStreamingAgent(middleware, _agent);
    }

    private sealed class DelegateStreamingAgent : IStreamingAgent
    {
        private IStreamingMiddleware? streamingMiddleware;
        private IStreamingAgent innerAgent;

        public string Name => innerAgent.Name;

        public DelegateStreamingAgent(IStreamingMiddleware middleware, IStreamingAgent next)
        {
            this.streamingMiddleware = middleware;
            this.innerAgent = next;
        }

        public Task<IMessage> GenerateReplyAsync(IEnumerable<IMessage> messages, GenerateReplyOptions? options = null, CancellationToken cancellationToken = default)
        {
            if (this.streamingMiddleware is null)
            {
                return innerAgent.GenerateReplyAsync(messages, options, cancellationToken);
            }

            var context = new MiddlewareContext(messages, options);
            return this.streamingMiddleware.InvokeAsync(context, (IAgent)innerAgent, cancellationToken);
        }

        public IAsyncEnumerable<IMessage> GenerateStreamingReplyAsync(IEnumerable<IMessage> messages, GenerateReplyOptions? options = null, CancellationToken cancellationToken = default)
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

public sealed class MiddlewareStreamingAgent<T> : MiddlewareStreamingAgent, IMiddlewareStreamAgent<T>
    where T : IStreamingAgent
{
    public MiddlewareStreamingAgent(T innerAgent, string? name = null, IEnumerable<IStreamingMiddleware>? streamingMiddlewares = null)
        : base(innerAgent, name, streamingMiddlewares)
    {
        TStreamingAgent = innerAgent;
    }

    public MiddlewareStreamingAgent(MiddlewareStreamingAgent<T> other)
        : base(other)
    {
        TStreamingAgent = other.TStreamingAgent;
    }

    /// <summary>
    /// Get the inner agent.
    /// </summary>
    public T TStreamingAgent { get; }
}
