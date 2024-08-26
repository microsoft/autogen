// Copyright (c) 2023 - 2024, Owners of https://github.com/autogen-ai
// SPDX-License-Identifier: Apache-2.0
// Contributions to this project, i.e., https://github.com/autogen-ai/autogen, 
// are licensed under the Apache License, Version 2.0 (Apache-2.0).
// Portions derived from  https://github.com/microsoft/autogen under the MIT License.
// SPDX-License-Identifier: MIT
// Copyright (c) Microsoft Corporation. All rights reserved.
// IMiddleware.cs

using System.Threading;
using System.Threading.Tasks;

namespace AutoGen.Core;

/// <summary>
/// The middleware interface. For streaming-version middleware, check <see cref="IStreamingMiddleware"/>.
/// </summary>
public interface IMiddleware
{
    /// <summary>
    /// the name of the middleware
    /// </summary>
    public string? Name { get; }

    /// <summary>
    /// The method to invoke the middleware
    /// </summary>
    public Task<IMessage> InvokeAsync(
        MiddlewareContext context,
        IAgent agent,
        CancellationToken cancellationToken = default);
}
