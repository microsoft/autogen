// Copyright (c) 2023 - 2024, Owners of https://github.com/autogen-ai
// SPDX-License-Identifier: Apache-2.0
// Contributions to this project, i.e., https://github.com/autogen-ai/autogen, 
// are licensed under the Apache License, Version 2.0 (Apache-2.0).
// Portions derived from  https://github.com/microsoft/autogen under the MIT License.
// SPDX-License-Identifier: MIT
// Copyright (c) Microsoft Corporation. All rights reserved.
// PrintMessageMiddlewareExtension.cs

using System;

namespace AutoGen.Core;

public static class PrintMessageMiddlewareExtension
{
    [Obsolete("This API will be removed in v0.1.0, Use RegisterPrintMessage instead.")]
    public static MiddlewareAgent<TAgent> RegisterPrintFormatMessageHook<TAgent>(this TAgent agent)
        where TAgent : IAgent
    {
        return RegisterPrintMessage(agent);
    }

    [Obsolete("This API will be removed in v0.1.0, Use RegisterPrintMessage instead.")]
    public static MiddlewareAgent<TAgent> RegisterPrintFormatMessageHook<TAgent>(this MiddlewareAgent<TAgent> agent)
        where TAgent : IAgent
    {
        return RegisterPrintMessage(agent);
    }

    [Obsolete("This API will be removed in v0.1.0, Use RegisterPrintMessage instead.")]
    public static MiddlewareStreamingAgent<TAgent> RegisterPrintFormatMessageHook<TAgent>(this MiddlewareStreamingAgent<TAgent> agent)
        where TAgent : IStreamingAgent
    {
        return RegisterPrintMessage(agent);
    }

    /// <summary>
    /// Register a <see cref="PrintMessageMiddleware"/> to <paramref name="agent"/> which print formatted message to console.
    /// </summary>
    public static MiddlewareAgent<TAgent> RegisterPrintMessage<TAgent>(this TAgent agent)
        where TAgent : IAgent
    {
        var middleware = new PrintMessageMiddleware();
        var middlewareAgent = new MiddlewareAgent<TAgent>(agent);
        middlewareAgent.Use(middleware);

        return middlewareAgent;
    }

    /// <summary>
    /// Register a <see cref="PrintMessageMiddleware"/> to <paramref name="agent"/> which print formatted message to console.
    /// </summary>
    public static MiddlewareAgent<TAgent> RegisterPrintMessage<TAgent>(this MiddlewareAgent<TAgent> agent)
        where TAgent : IAgent
    {
        var middleware = new PrintMessageMiddleware();
        var middlewareAgent = new MiddlewareAgent<TAgent>(agent);
        middlewareAgent.Use(middleware);

        return middlewareAgent;
    }

    /// <summary>
    /// Register a <see cref="PrintMessageMiddleware"/> to <paramref name="agent"/> which print formatted message to console.
    /// </summary>
    public static MiddlewareStreamingAgent<TAgent> RegisterPrintMessage<TAgent>(this MiddlewareStreamingAgent<TAgent> agent)
        where TAgent : IStreamingAgent
    {
        var middleware = new PrintMessageMiddleware();
        var middlewareAgent = new MiddlewareStreamingAgent<TAgent>(agent);
        middlewareAgent.UseStreaming(middleware);

        return middlewareAgent;
    }
}
