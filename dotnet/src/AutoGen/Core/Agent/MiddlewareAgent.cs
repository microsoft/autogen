// Copyright (c) Microsoft Corporation. All rights reserved.
// MiddlewareAgent.cs

using System.Collections.Generic;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;

namespace AutoGen;

public delegate Task<Message> GenerateReplyDelegate(
    IEnumerable<Message> messages,
    GenerateReplyOptions? options,
    CancellationToken cancellationToken);

/// <summary>
/// middleware delegate. Call into the next function to continue the execution of the next middleware. Otherwise, short cut the middleware execution.
/// </summary>
/// <param name="messages">messages to process</param>
/// <param name="options">options</param>
/// <param name="cancellationToken">cancellation token</param>
/// <param name="next">next middleware</param>
public delegate Task<Message> MiddlewareDelegate(
       IEnumerable<Message> messages,
       GenerateReplyOptions? options,
       GenerateReplyDelegate next,
       CancellationToken cancellationToken);

/// <summary>
/// An agent that allows you to add middleware and modify the behavior of an existing agent.
/// </summary>
public class MiddlewareAgent : IAgent
{
    private readonly IAgent innerAgent;
    private readonly List<MiddlewareDelegate> middlewares = new();

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
        var middleware = this.middlewares.Aggregate(
                       (GenerateReplyDelegate)this.innerAgent.GenerateReplyAsync,
                       (next, current) => (messages, options, cancellationToken) => current(messages, options, next, cancellationToken));

        return middleware(messages, options, cancellationToken);
    }

    /// <summary>
    /// Add a middleware to the agent. If multiple middlewares are added, they will be executed in the LIFO order.
    /// Call into the next function to continue the execution of the next middleware.
    /// Short cut middleware execution by not calling into the next function.
    /// </summary>
    public void Use(MiddlewareDelegate func)
    {
        this.middlewares.Add(func);
    }
}
