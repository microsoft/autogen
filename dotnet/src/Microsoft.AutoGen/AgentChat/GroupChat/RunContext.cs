// Copyright (c) Microsoft Corporation. All rights reserved.
// RunContext.cs

using System.Diagnostics;
using System.Runtime.CompilerServices;

namespace Microsoft.AutoGen.AgentChat.GroupChat;

public abstract class LifecycleObject
{
    private int initialized;

    private void PrepareInitialize(Action errorAction)
    {
        if (Interlocked.CompareExchange(ref this.initialized, 1, 0) != 0)
        {
            errorAction();
        }
    }

    private void PrepareDeinitialize(Action errorAction)
    {
        if (Interlocked.CompareExchange(ref this.initialized, 0, 1) != 1)
        {
            errorAction();
        }
    }

    protected bool IsInitialized => Volatile.Read(ref this.initialized) == 1;

    protected virtual void OnInitializeError() => throw new InvalidOperationException($"Error initializing: {this.GetType().FullName}; already initialized.");
    protected virtual void OnDeinitializeError() => throw new InvalidOperationException($"Error deinitializing: {this.GetType().FullName}; not initialized.");

    public ValueTask InitializeAsync()
    {
        this.PrepareInitialize(this.OnInitializeError);
        return this.InitializeCore();
    }

    public ValueTask DeinitializeAsync()
    {
        this.PrepareDeinitialize(this.OnDeinitializeError);
        return this.DeinitializeCore();
    }

    protected abstract ValueTask InitializeCore();
    protected abstract ValueTask DeinitializeCore();
}

public interface IRunContextLayer
{
    public ValueTask InitializeAsync();
    public ValueTask DeinitializeAsync();
}

public sealed class RunContextStack : LifecycleObject, IRunContextLayer
{
    private Stack<IRunContextLayer> Uninitialized { get; } = new();
    private Stack<IRunContextLayer> Initialized { get; } = new();

    public RunContextStack(params IEnumerable<IRunContextLayer> contextLayers)
    {
        this.Uninitialized = new Stack<IRunContextLayer>(contextLayers);
    }

    // TODO: There is probably a way to have a sound manner by which pushing/popping a layer when initialized
    // would be allowed. But this is not necessary for now, so we will keep it simple.
    public void PushLayer(IRunContextLayer layer)
    {
        if (this.IsInitialized)
        {
            throw new InvalidOperationException("Cannot push a layer while the context is initialized.");
        }

        this.Uninitialized.Push(layer);
    }

    public void PopLayer()
    {
        if (this.IsInitialized)
        {
            throw new InvalidOperationException("Cannot pop a layer while the context is initialized.");
        }
    }

    private Action? initializeError;
    protected override void OnInitializeError()
    {
        (this.initializeError ?? base.OnInitializeError)();
    }

    private Action? deinitializeError;
    protected override void OnDeinitializeError()
    {
        (this.deinitializeError ?? base.OnDeinitializeError)();
    }

    public static IRunContextLayer OverrideErrors(Action? initializeError = null, Action? deinitializeError = null)
    {
        return new ErrorOverrideLayer(initializeError, deinitializeError);
    }

    private sealed class ErrorOverrideLayer(Action? initializeError = null, Action? deinitializeError = null)
        : IRunContextLayer
    {
        public RunContextStack? Target { get; set; }

        private Action? initializeErrorPrev;
        private Action? deinitializeErrorPrev;

        public ValueTask InitializeAsync()
        {
            if (initializeError != null)
            {
                this.initializeErrorPrev = Interlocked.CompareExchange(ref this.Target!.initializeError, initializeError, null);
            }

            if (deinitializeError != null)
            {
                this.deinitializeErrorPrev = Interlocked.CompareExchange(ref this.Target!.deinitializeError, deinitializeError, null);
            }

            return ValueTask.CompletedTask;
        }

        public ValueTask DeinitializeAsync()
        {
            if (this.initializeErrorPrev != null)
            {
                Interlocked.CompareExchange(ref this.Target!.initializeError, this.initializeErrorPrev, initializeError);
            }

            if (this.deinitializeErrorPrev != null)
            {
                Interlocked.CompareExchange(ref this.Target!.deinitializeError, this.deinitializeErrorPrev, deinitializeError);
            }

            return ValueTask.CompletedTask;
        }
    }

    public ValueTask<IAsyncDisposable> Enter()
    {
        return RunTicket.Enter(this);
    }

    protected override async ValueTask InitializeCore()
    {
        while (this.Uninitialized.Count > 0)
        {
            IRunContextLayer layer = this.Uninitialized.Pop();
            if (layer is ErrorOverrideLayer errorOverrideLayer)
            {
                errorOverrideLayer.Target = this;
            }

            await layer.InitializeAsync();
            this.Initialized.Push(layer);
        }
    }

    protected override async ValueTask DeinitializeCore()
    {
        while (this.Initialized.Count > 0)
        {
            IRunContextLayer layer = this.Initialized.Pop();
            await layer.DeinitializeAsync();
            this.Uninitialized.Push(layer);
        }
    }

    private sealed class RunTicket : IAsyncDisposable
    {
        private RunContextStack contextStack;
        private int disposed;

        private RunTicket(RunContextStack contextStack)
        {
            Debug.Assert(contextStack.IsInitialized, "The context stack must be initialized.");
            this.contextStack = contextStack;
        }

        public static async ValueTask<IAsyncDisposable> Enter(RunContextStack contextStack)
        {
            await contextStack.InitializeAsync();
            return new RunTicket(contextStack);
        }

        public ValueTask DisposeAsync()
        {
            if (Interlocked.CompareExchange(ref this.disposed, 1, 0) == 0)
            {
                return this.contextStack.DeinitializeAsync();
            }

            return ValueTask.CompletedTask;
        }
    }
}

public sealed class RunManager
{
    private RunContextStack runContextStack;

    public RunManager(params IEnumerable<IRunContextLayer> contextLayers)
    {
        this.runContextStack = new RunContextStack(contextLayers);
    }

    private ValueTask<IAsyncDisposable> PrepareRunAsync(string? message = null)
    {
        if (message != null)
        {
            IRunContextLayer errorOverride = RunContextStack.OverrideErrors(() => throw new InvalidOperationException(message));
            this.runContextStack.PushLayer(errorOverride);
        }

        return this.runContextStack.Enter();
    }

    private async ValueTask EndRunAsync(IAsyncDisposable? runDisposable, bool hadMessage)
    {
        if (runDisposable != null)
        {
            await runDisposable.DisposeAsync().ConfigureAwait(false);
        }

        if (hadMessage)
        {
            this.runContextStack.PopLayer();
        }
    }

    public async ValueTask RunAsync(Func<CancellationToken, ValueTask> asyncAction, CancellationToken cancellation = default, Func<CancellationToken, ValueTask>? prepareAction = null, string? message = null)
    {
        IAsyncDisposable? runDisposable = null;
        try
        {
            runDisposable = await this.PrepareRunAsync(message).ConfigureAwait(false);

            if (prepareAction != null)
            {
                await prepareAction(cancellation).ConfigureAwait(false);
            }

            await asyncAction(cancellation).ConfigureAwait(false);
        }
        finally
        {
            await this.EndRunAsync(runDisposable, message != null).ConfigureAwait(false);
        }
    }

    public async ValueTask<T> RunAsync<T>(Func<CancellationToken, ValueTask<T>> asyncAction, CancellationToken cancellation = default, Func<CancellationToken, ValueTask>? prepareAction = null, string? message = null)
    {
        IAsyncDisposable? runDisposable = null;
        try
        {
            runDisposable = await this.PrepareRunAsync(message).ConfigureAwait(false);

            if (prepareAction != null)
            {
                await prepareAction(cancellation).ConfigureAwait(false);
            }

            return await asyncAction(cancellation).ConfigureAwait(false);
        }
        finally
        {
            await this.EndRunAsync(runDisposable, message != null).ConfigureAwait(false);
        }
    }

    public async IAsyncEnumerable<TItem> StreamAsync<TItem>(Func<CancellationToken, IAsyncEnumerable<TItem>> streamAction, [EnumeratorCancellation] CancellationToken cancellation = default, Func<CancellationToken, ValueTask>? prepareAction = null, string? message = null)
    {
        IAsyncDisposable? runDisposable = null;
        try
        {
            runDisposable = await this.PrepareRunAsync(message).ConfigureAwait(false);

            if (prepareAction != null)
            {
                await prepareAction(cancellation).ConfigureAwait(false);
            }

            await foreach (TItem item in streamAction(cancellation))
            {
                yield return item;
            }
        }
        finally
        {
            await this.EndRunAsync(runDisposable, message != null).ConfigureAwait(false);
        }
    }
}

