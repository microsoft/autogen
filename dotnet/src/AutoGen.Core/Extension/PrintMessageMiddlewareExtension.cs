// Copyright (c) Microsoft Corporation. All rights reserved.
// PrintMessageMiddlewareExtension.cs

namespace AutoGen.Core;

public static class PrintMessageMiddlewareExtension
{
    /// <summary>
    /// Print formatted message to console.
    /// </summary>
    public static MiddlewareAgent<TAgent> RegisterPrintFormatMessageHook<TAgent>(this TAgent agent)
        where TAgent : IAgent
    {
        var middleware = new PrintMessageMiddleware();
        var middlewareAgent = new MiddlewareAgent<TAgent>(agent);
        middlewareAgent.Use(middleware);

        return middlewareAgent;
    }

    public static MiddlewareAgent<TAgent> RegisterPrintFormatMessageHook<TAgent>(this MiddlewareAgent<TAgent> agent)
        where TAgent : IAgent
    {
        var middleware = new PrintMessageMiddleware();
        var middlewareAgent = new MiddlewareAgent<TAgent>(agent);
        middlewareAgent.Use(middleware);

        return middlewareAgent;
    }

    public static MiddlewareStreamingAgent<TAgent> RegisterPrintFormatMessageHook<TAgent>(this MiddlewareStreamingAgent<TAgent> agent)
        where TAgent : IStreamingAgent
    {
        var middleware = new PrintMessageMiddleware();
        var middlewareAgent = new MiddlewareStreamingAgent<TAgent>(agent);
        middlewareAgent.Use(middleware);

        return middlewareAgent;
    }
}
