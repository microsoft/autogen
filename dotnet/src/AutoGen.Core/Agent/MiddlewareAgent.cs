// Copyright (c) Microsoft Corporation. All rights reserved.
// MiddlewareAgent.cs

using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;

namespace AutoGen.Core;

/// <summary>
/// An agent that allows you to add middleware and modify the behavior of an existing agent.
/// </summary>
public class MiddlewareAgent : IMiddlewareAgent
{
    private IAgent _agent;
    private readonly List<IMiddleware> middlewares = new();

    /// <summary>
    /// Create a new instance of <see cref="MiddlewareAgent"/>
    /// </summary>
    /// <param name="innerAgent">the inner agent where middleware will be added.</param>
    /// <param name="name">the name of the agent if provided. Otherwise, the name of <paramref name="innerAgent"/> will be used.</param>
    public MiddlewareAgent(IAgent innerAgent, string? name = null, IEnumerable<IMiddleware>? middlewares = null)
    {
        this.Name = name ?? innerAgent.Name;
        this._agent = innerAgent;
        if (middlewares != null && middlewares.Any())
        {
            foreach (var middleware in middlewares)
            {
                this.Use(middleware);
            }
        }
    }

    /// <summary>
    /// Create a new instance of <see cref="MiddlewareAgent"/> by copying the middlewares from another <see cref="MiddlewareAgent"/>.
    /// </summary>
    public MiddlewareAgent(MiddlewareAgent other)
    {
        this.Name = other.Name;
        this._agent = other._agent;
        this.middlewares.AddRange(other.middlewares);
    }

    public string Name { get; }

    /// <summary>
    /// Get the inner agent.
    /// </summary>
    public IAgent Agent => this._agent;

    /// <summary>
    /// Get the middlewares.
    /// </summary>
    public IEnumerable<IMiddleware> Middlewares => this.middlewares;

    public Task<IMessage> GenerateReplyAsync(
        IEnumerable<IMessage> messages,
        GenerateReplyOptions? options = null,
        CancellationToken cancellationToken = default)
    {
        return _agent.GenerateReplyAsync(messages, options, cancellationToken);
    }

    /// <summary>
    /// Add a middleware to the agent. If multiple middlewares are added, they will be executed in the LIFO order.
    /// Call into the next function to continue the execution of the next middleware.
    /// Short cut middleware execution by not calling into the next function.
    /// </summary>
    public void Use(Func<IEnumerable<IMessage>, GenerateReplyOptions?, IAgent, CancellationToken, Task<IMessage>> func, string? middlewareName = null)
    {
        var middleware = new DelegateMiddleware(middlewareName, async (context, agent, cancellationToken) =>
        {
            return await func(context.Messages, context.Options, agent, cancellationToken);
        });

        this.Use(middleware);
    }

    public void Use(IMiddleware middleware)
    {
        this.middlewares.Add(middleware);
        _agent = new DelegateAgent(middleware, _agent);
    }

    public override string ToString()
    {
        var names = this.Middlewares.Select(m => m.Name ?? "[Unknown middleware]");
        var namesPlusAgentName = names.Append(this.Name);

        return namesPlusAgentName.Aggregate((a, b) => $"{a} -> {b}");
    }

    private sealed class DelegateAgent : IAgent
    {
        private readonly IAgent innerAgent;
        private readonly IMiddleware middleware;

        public DelegateAgent(IMiddleware middleware, IAgent innerAgent)
        {
            this.middleware = middleware;
            this.innerAgent = innerAgent;
        }

        public string Name { get => this.innerAgent.Name; }

        public Task<IMessage> GenerateReplyAsync(
            IEnumerable<IMessage> messages,
            GenerateReplyOptions? options = null,
            CancellationToken cancellationToken = default)
        {
            var context = new MiddlewareContext(messages, options);
            return this.middleware.InvokeAsync(context, this.innerAgent, cancellationToken);
        }
    }
}

public sealed class MiddlewareAgent<T> : MiddlewareAgent, IMiddlewareAgent<T>
    where T : IAgent
{
    public MiddlewareAgent(T innerAgent, string? name = null)
        : base(innerAgent, name)
    {
        this.TAgent = innerAgent;
    }

    public MiddlewareAgent(MiddlewareAgent<T> other)
        : base(other)
    {
        this.TAgent = other.TAgent;
    }

    /// <summary>
    /// Get the inner agent of type <typeparamref name="T"/>.
    /// </summary>
    public T TAgent { get; }
}
