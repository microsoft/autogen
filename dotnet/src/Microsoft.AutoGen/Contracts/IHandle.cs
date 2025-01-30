// Copyright (c) Microsoft Corporation. All rights reserved.
// IHandle.cs

namespace Microsoft.AutoGen.Contracts;

/// <summary>
/// Defines a handler interface for processing items of type <typeparamref name="T"/>.
/// </summary>
/// <typeparam name="T">The type of item to be handled.</typeparam>
public interface IHandle<in T>
{
    /// <summary>
    /// Handles the specified item asynchronously.
    /// </summary>
    /// <param name="item">The item to be handled.</param>
    /// <returns>A task that represents the asynchronous operation.</returns>
    ValueTask HandleAsync(T item, MessageContext messageContext);
}

public interface IHandle<in InT, OutT>
{
    /// <summary>
    /// Handles the specified item asynchronously.
    /// </summary>
    /// <param name="item">The item to be handled.</param>
    /// <returns>A task that represents the asynchronous operation.</returns>
    ValueTask<OutT> HandleAsync(InT item, MessageContext messageContext);
}
