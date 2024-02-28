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

    public string? Name { get; }

    public async Task<Message> GenerateReplyAsync(IEnumerable<Message> messages, GenerateReplyOptions? options = null, CancellationToken cancellationToken = default)
    {
        var reply = await GenerateStreamingReplyAsync(messages, options, cancellationToken);
        Message? result = default;

        await foreach (var message in reply.WithCancellation(cancellationToken))
        {
            result = message;
        }

        return result ?? throw new InvalidOperationException("No message returned from the streaming agent.");
    }

    public Task<IAsyncEnumerable<Message>> GenerateStreamingReplyAsync(IEnumerable<Message> messages, GenerateReplyOptions? options = null, CancellationToken cancellationToken = default)
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

    public void Use(Func<MiddlewareContext, IStreamingAgent, CancellationToken, Task<IAsyncEnumerable<Message>>> func, string? middlewareName = null)
    {
        _middlewares.Add(new DelegateStreamingMiddleware(middlewareName, new DelegateStreamingMiddleware.MiddlewareDelegate(func)));
    }

    private class DelegateStreamingAgent : IStreamingAgent
    {
        private IStreamingMiddleware middleware;
        private IStreamingAgent innerAgent;

        public string? Name => innerAgent.Name;

        public DelegateStreamingAgent(IStreamingMiddleware middleware, IStreamingAgent next)
        {
            this.middleware = middleware;
            this.innerAgent = next;
        }

        public async Task<Message> GenerateReplyAsync(IEnumerable<Message> messages, GenerateReplyOptions? options = null, CancellationToken cancellationToken = default)
        {
            var stream = await GenerateStreamingReplyAsync(messages, options, cancellationToken);
            var result = default(Message);

            await foreach (var message in stream.WithCancellation(cancellationToken))
            {
                result = message;
            }

            return result ?? throw new InvalidOperationException("No message returned from the streaming agent.");
        }

        public Task<IAsyncEnumerable<Message>> GenerateStreamingReplyAsync(IEnumerable<Message> messages, GenerateReplyOptions? options = null, CancellationToken cancellationToken = default)
        {
            var context = new MiddlewareContext(messages, options);
            return middleware.InvokeAsync(context, innerAgent, cancellationToken);
        }
    }
}
