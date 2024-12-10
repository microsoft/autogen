// Copyright (c) Microsoft Corporation. All rights reserved.
// IHandle.cs

namespace Microsoft.AutoGen.Abstractions;

public interface IHandle
{
    Task HandleObject(object item);
}

public interface IHandle<in T> : IHandle
{
    // TODO: Should this be a ValueTask?
    Task Handle(T item);
}

public interface IHandleEx<in TIn> : IHandle<TIn>
{
    Task IHandle<TIn>.Handle(TIn item)
    {
        return this.HandleAsync(item, CancellationToken.None).AsTask();
    }

    ValueTask HandleAsync(TIn item)
    {
        return this.HandleAsync(item, CancellationToken.None);
    }

    ValueTask HandleAsync(TIn item, CancellationToken cancellationToken);
}

public interface IHandleEx<in TIn, TOut> // TODO: Map this to IHandle<> somehow?
{
    ValueTask<TOut> HandleAsync(TIn item)
    {
        return this.HandleAsync(item, CancellationToken.None);
    }

    ValueTask<TOut> HandleAsync(TIn item, CancellationToken cancellationToken);
}

public interface IHandleDefault : IHandleEx<object>
{
}

public interface IHandleStream<in TIn, TOut>
{
    IAsyncEnumerable<TOut> StreamAsync(TIn item)
    {
        return this.StreamAsync(item, CancellationToken.None);
    }

    IAsyncEnumerable<TOut> StreamAsync(TIn item, CancellationToken cancellationToken);
}
