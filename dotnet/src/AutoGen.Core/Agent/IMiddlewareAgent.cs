// Copyright (c) 2023 - 2024, Owners of https://github.com/autogen-ai
// SPDX-License-Identifier: Apache-2.0
// Contributions to this project, i.e., https://github.com/autogen-ai/autogen, 
// are licensed under the Apache License, Version 2.0 (Apache-2.0).
// Portions derived from  https://github.com/microsoft/autogen under the MIT License.
// SPDX-License-Identifier: MIT
// Copyright (c) Microsoft Corporation. All rights reserved.
// IMiddlewareAgent.cs

using System.Collections.Generic;

namespace AutoGen.Core;

public interface IMiddlewareAgent : IAgent
{
    /// <summary>
    /// Get the inner agent.
    /// </summary>
    IAgent Agent { get; }

    /// <summary>
    /// Get the middlewares.
    /// </summary>
    IEnumerable<IMiddleware> Middlewares { get; }

    /// <summary>
    /// Use middleware.
    /// </summary>
    void Use(IMiddleware middleware);
}

public interface IMiddlewareStreamAgent : IStreamingAgent
{
    /// <summary>
    /// Get the inner agent.
    /// </summary>
    IStreamingAgent StreamingAgent { get; }

    IEnumerable<IStreamingMiddleware> StreamingMiddlewares { get; }

    void UseStreaming(IStreamingMiddleware middleware);
}

public interface IMiddlewareAgent<out T> : IMiddlewareAgent
    where T : IAgent
{
    /// <summary>
    /// Get the typed inner agent.
    /// </summary>
    T TAgent { get; }
}

public interface IMiddlewareStreamAgent<out T> : IMiddlewareStreamAgent
    where T : IStreamingAgent
{
    /// <summary>
    /// Get the typed inner agent.
    /// </summary>
    T TStreamingAgent { get; }
}
