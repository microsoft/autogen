// Copyright (c) Microsoft Corporation. All rights reserved.
// MessageHandling.cs

namespace Microsoft.AutoGen.AgentChat.Abstractions;

public interface IHandleChat<in TIn>
{
    ValueTask HandleAsync(TIn item)
    {
        return this.HandleAsync(item, CancellationToken.None);
    }

    ValueTask HandleAsync(TIn item, CancellationToken cancellationToken);
}

public interface IHandleChat<in TIn, TOut> // TODO: Map this to IHandle<> somehow?
{
    ValueTask<TOut> HandleAsync(TIn item)
    {
        return this.HandleAsync(item, CancellationToken.None);
    }

    ValueTask<TOut> HandleAsync(TIn item, CancellationToken cancellationToken);
}

public interface IHandleDefault : IHandleChat<object>
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
