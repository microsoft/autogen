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

public delegate Task<IAsyncEnumerable<Message>> GenerateReplyStreamingDelegate(
       IEnumerable<Message> messages,
       GenerateReplyOptions? options,
       CancellationToken cancellationToken);

public delegate Task<IAsyncEnumerable<Message>> MiddlewareStreamingDelegate(
    IEnumerable<Message> messages,
    GenerateReplyOptions? options,
    GenerateReplyStreamingDelegate next,
    CancellationToken cancellationToken);

/// <summary>
/// An agent that allows you to add middleware and modify the behavior of an existing agent.
/// </summary>
public class MiddlewareAgent : IStreamingReplyAgent
{
    private readonly IAgent innerAgent;
    private readonly List<MiddlewareStreamingDelegate> middlewares = new();

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
                ToGenerateReplyStreamingDelegate(this.innerAgent.GenerateReplyAsync),
                (next, current) => (messages, options, cancellationToken) => current(messages, options, next, cancellationToken));

        return ToGenerateReplyDelegate(middleware)(messages, options, cancellationToken);
    }

    public async Task<IAsyncEnumerable<Message>> GenerateReplyStreamingAsync(IEnumerable<Message> messages, GenerateReplyOptions? options = null, CancellationToken cancellationToken = default)
    {
        if (this.innerAgent is IStreamingReplyAgent streamingReplyAgent)
        {
            var middleware = this.middlewares.Aggregate(
                (GenerateReplyStreamingDelegate)streamingReplyAgent.GenerateReplyStreamingAsync,
                (next, current) => (messages, options, cancellationToken) => current(messages, options, next, cancellationToken));

            return await middleware(messages, options, cancellationToken);
        }
        else
        {
            var msg = await this.GenerateReplyAsync(messages, options, cancellationToken);

            return this.From(msg);
        }
    }

    /// <summary>
    /// Add a middleware to the agent. If multiple middlewares are added, they will be executed in the LIFO order.
    /// Call into the next function to continue the execution of the next middleware.
    /// Short cut middleware execution by not calling into the next function.
    /// </summary>
    public void Use(MiddlewareDelegate func)
    {
        this.middlewares.Add(async (messages, options, next, ct) =>
        {
            var funcNext = ToGenerateReplyDelegate(next);
            var reply = await func(messages, options, funcNext, ct);

            return this.From(reply);
        });
    }

    public void UseStreaming(MiddlewareStreamingDelegate func)
    {
        this.middlewares.Add(func);
    }

    private async IAsyncEnumerable<T> From<T>(T value)
    {
        yield return value;
    }

    private GenerateReplyStreamingDelegate ToGenerateReplyStreamingDelegate(GenerateReplyDelegate func)
    {
        return async (messages, options, ct) =>
        {
            var reply = await func(messages, options, ct);

            return this.From(reply);
        };
    }

    private GenerateReplyDelegate ToGenerateReplyDelegate(GenerateReplyStreamingDelegate func)
    {
        return async (messages, options, ct) =>
        {
            Message? msg = default;
            var response = await func(messages, options, ct);
            await foreach (var result in response)
            {
                msg = result;
            }

            return msg ?? throw new System.Exception("No result is returned.");
        };
    }
}
