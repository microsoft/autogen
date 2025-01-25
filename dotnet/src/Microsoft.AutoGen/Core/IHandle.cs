// Copyright (c) Microsoft Corporation. All rights reserved.
// IHandle.cs

using Google.Protobuf;

namespace Microsoft.AutoGen.Core;

/// <summary>
/// Defines a handler interface for processing items of type <typeparamref name="T"/>.
/// </summary>
/// <typeparam name="T">The type of item to be handled, which must implement <see cref="IMessage"/>.</typeparam>
public interface IHandle<in T> where T : IMessage
{
    /// <summary>
    /// Handles the specified item asynchronously.
    /// </summary>
    /// <param name="item">The item to be handled.</param>
    /// <returns>A task that represents the asynchronous operation.</returns>
    Task Handle(T item, CancellationToken cancellationToken = default);
}
