// Copyright (c) Microsoft Corporation. All rights reserved.
// MiddlewareAgent.cs

using System;
using System.Collections.Generic;
using System.Threading;
using System.Threading.Tasks;
using AutoGen.Core.Middleware;

namespace AutoGen;

/// <summary>
/// An agent that allows you to add middleware and modify the behavior of an existing agent.
/// </summary>
public class MiddlewareAgent : IAgent
{
    private readonly IAgent innerAgent;
    private readonly List<IMiddleware> middlewares = new();

    /// <summary>
    /// Create a new instance of <see cref="MiddlewareAgent"/>
    /// </summary>
    /// <param name="innerAgent">the inner agent where middleware will be added.</param>
    /// <param name="name">the name of the agent if provided. Otherwise, the name of <paramref name="innerAgent"/> will be used.</param>
    public MiddlewareAgent(IAgent innerAgent, string? name = null)
    {
        this.innerAgent = innerAgent;
        this.Name = name ?? innerAgent.Name;
    }

    public string? Name { get; }

    public Task<Message> GenerateReplyAsync(
        IEnumerable<Message> messages,
        GenerateReplyOptions? options = null,
        CancellationToken cancellationToken = default)
    {
        var agent = this.innerAgent;
        foreach (var middleware in this.middlewares)
        {
            agent = new DelegateAgent(middleware, agent);
        }

        return agent.GenerateReplyAsync(messages, options, cancellationToken);
    }

    /// <summary>
    /// Add a middleware to the agent. If multiple middlewares are added, they will be executed in the LIFO order.
    /// Call into the next function to continue the execution of the next middleware.
    /// Short cut middleware execution by not calling into the next function.
    /// </summary>
    public void Use(Func<IEnumerable<Message>, GenerateReplyOptions?, IAgent, CancellationToken, Task<Message>> func, string? middlewareName = null)
    {
        this.middlewares.Add(new DelegateMiddleware(middlewareName, async (context, agent, cancellationToken) =>
        {
            return await func(context.Messages, context.Options, agent, cancellationToken);
        }));
    }

    public void Use(Func<MiddlewareContext, IAgent, CancellationToken, Task<Message>> func, string? middlewareName = null)
    {
        this.middlewares.Add(new DelegateMiddleware(middlewareName, func));
    }

    public void Use(IMiddleware middleware)
    {
        this.middlewares.Add(middleware);
    }
}

internal class DelegateAgent : IAgent
{
    private readonly IAgent innerAgent;
    private readonly IMiddleware middleware;

    public DelegateAgent(IMiddleware middleware, IAgent innerAgent)
    {
        this.middleware = middleware;
        this.innerAgent = innerAgent;
    }

    public string? Name { get => this.innerAgent.Name; }

    public Task<Message> GenerateReplyAsync(
        IEnumerable<Message> messages,
        GenerateReplyOptions? options = null,
        CancellationToken cancellationToken = default)
    {
        var context = new MiddlewareContext(messages, options);
        return this.middleware.InvokeAsync(context, this.innerAgent, cancellationToken);
    }
}
