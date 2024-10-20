// Copyright (c) 2023 - 2024, Owners of https://github.com/autogenhub
// SPDX-License-Identifier: Apache-2.0
// Contributions to this project, i.e., https://github.com/autogenhub/autogen, 
// are licensed under the Apache License, Version 2.0 (Apache-2.0).
// Portions derived from  https://github.com/microsoft/autogen under the MIT License.
// SPDX-License-Identifier: MIT
// Copyright (c) Microsoft Corporation. All rights reserved.
// DelegateMiddleware.cs

using System;
using System.Threading;
using System.Threading.Tasks;

namespace AutoGen.Core;

internal class DelegateMiddleware : IMiddleware
{
    /// <summary>
    /// middleware delegate. Call into the next function to continue the execution of the next middleware. Otherwise, short cut the middleware execution.
    /// </summary>
    /// <param name="cancellationToken">cancellation token</param>
    public delegate Task<IMessage> MiddlewareDelegate(
        MiddlewareContext context,
        IAgent agent,
        CancellationToken cancellationToken);

    private readonly MiddlewareDelegate middlewareDelegate;

    public DelegateMiddleware(string? name, Func<MiddlewareContext, IAgent, CancellationToken, Task<IMessage>> middlewareDelegate)
    {
        this.Name = name;
        this.middlewareDelegate = async (context, agent, cancellationToken) =>
        {
            return await middlewareDelegate(context, agent, cancellationToken);
        };
    }

    public string? Name { get; }

    public Task<IMessage> InvokeAsync(
        MiddlewareContext context,
        IAgent agent,
        CancellationToken cancellationToken = default)
    {
        var messages = context.Messages;
        var options = context.Options;

        return this.middlewareDelegate(context, agent, cancellationToken);
    }
}

