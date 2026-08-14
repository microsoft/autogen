// Copyright (c) Microsoft Corporation. All rights reserved.
// StreamingMiddlewareExtension.cs

namespace AutoGen.Core;

public static class StreamingMiddlewareExtension
{
    /// <summary>
    /// Register an <see cref="IStreamingMiddleware"/> to an existing <see cref="IStreamingAgent"/> and return a new agent with the registered middleware.
    /// For registering an <see cref="IMiddleware"/>, please refer to <see cref="MiddlewareExtension.RegisterMiddleware{TAgent}(MiddlewareAgent{TAgent}, IMiddleware)"/>
    /// </summary>
    public static MiddlewareStreamingAgent<TStreamingAgent> RegisterStreamingMiddleware<TStreamingAgent>(
        this TStreamingAgent agent,
        IStreamingMiddleware middleware)
        where TStreamingAgent : IStreamingAgent
    {
        var middlewareAgent = new MiddlewareStreamingAgent<TStreamingAgent>(agent);
        middlewareAgent.UseStreaming(middleware);

        return middlewareAgent;
    }

    /// <summary>
    /// Register an <see cref="IStreamingMiddleware"/> to an existing <see cref="IStreamingAgent"/> and return a new agent with the registered middleware.
    /// For registering an <see cref="IMiddleware"/>, please refer to <see cref="MiddlewareExtension.RegisterMiddleware{TAgent}(MiddlewareAgent{TAgent}, IMiddleware)"/>
    /// </summary>
    public static MiddlewareStreamingAgent<TAgent> RegisterStreamingMiddleware<TAgent>(
        this MiddlewareStreamingAgent<TAgent> agent,
        IStreamingMiddleware middleware)
        where TAgent : IStreamingAgent
    {
        var copyAgent = new MiddlewareStreamingAgent<TAgent>(agent);
        copyAgent.UseStreaming(middleware);

        return copyAgent;
    }
}
