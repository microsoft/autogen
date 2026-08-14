// Copyright (c) Microsoft Corporation. All rights reserved.
// MessageHandling.cs

namespace Microsoft.AutoGen.AgentChat.Abstractions;

public interface IHandleChat<in TIn>
{
    public ValueTask HandleAsync(TIn item)
    {
        return this.HandleAsync(item, CancellationToken.None);
    }

    public ValueTask HandleAsync(TIn item, CancellationToken cancellationToken);
}

public interface IHandleChat<in TIn, TOut> // TODO: Map this to IHandle<> somehow?
{
    public ValueTask<TOut> HandleAsync(TIn item)
    {
        return this.HandleAsync(item, CancellationToken.None);
    }

    public ValueTask<TOut> HandleAsync(TIn item, CancellationToken cancellationToken);
}

public interface IHandleDefault : IHandleChat<object>
{
}

public interface IHandleStream<in TIn, TOut>
{
    public IAsyncEnumerable<TOut> StreamAsync(TIn item)
    {
        return this.StreamAsync(item, CancellationToken.None);
    }

    public IAsyncEnumerable<TOut> StreamAsync(TIn item, CancellationToken cancellationToken);
}
