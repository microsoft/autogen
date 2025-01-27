// Copyright (c) Microsoft Corporation. All rights reserved.
// IHandle.cs

using Google.Protobuf;
using Microsoft.AutoGen.Contracts.Python;

namespace Microsoft.AutoGen.Core.Python;

/// <summary>
/// Defines a handler interface for processing items of type <typeparamref name="T"/>.
/// </summary>
/// <typeparam name="T">The type of item to be handled, which must implement <see cref="IMessage"/>.</typeparam>
public interface IHandle<in T>
{
    /// <summary>
    /// Handles the specified item asynchronously.
    /// </summary>
    /// <param name="item">The item to be handled.</param>
    /// <returns>A task that represents the asynchronous operation.</returns>
    Task Handle(T item, MessageContext messageContext);
}

public interface IHandle<in InT, OutT>
{
    /// <summary>
    /// Handles the specified item asynchronously.
    /// </summary>
    /// <param name="item">The item to be handled.</param>
    /// <returns>A task that represents the asynchronous operation.</returns>
    Task<OutT> Handle(InT item, MessageContext messageContext);
}
