// Copyright (c) Microsoft Corporation. All rights reserved.
// ResultSink.cs

using System.Threading.Tasks.Sources;

namespace Microsoft.AutoGen.Core;

internal interface IResultSink<TResult> : IValueTaskSource<TResult>
{
    void SetResult(TResult result);
    void SetException(Exception exception);
    void SetCancelled();

    ValueTask<TResult> Future { get; }
}

internal sealed class ResultSink<TResult> : IResultSink<TResult>
{
    private ManualResetValueTaskSourceCore<TResult> core;

    public TResult GetResult(short token)
    {
        return this.core.GetResult(token);
    }

    public ValueTaskSourceStatus GetStatus(short token)
    {
        return this.core.GetStatus(token);
    }

    public void OnCompleted(Action<object?> continuation, object? state, short token, ValueTaskSourceOnCompletedFlags flags)
    {
        this.core.OnCompleted(continuation, state, token, flags);
    }

    public bool IsCancelled { get; private set; }
    public void SetCancelled()
    {
        this.IsCancelled = true;
        this.core.SetException(new OperationCanceledException());
    }

    public void SetException(Exception exception)
    {
        this.core.SetException(exception);
    }

    public void SetResult(TResult result)
    {
        this.core.SetResult(result);
    }

    public ValueTask<TResult> Future => new(this, this.core.Version);
}
