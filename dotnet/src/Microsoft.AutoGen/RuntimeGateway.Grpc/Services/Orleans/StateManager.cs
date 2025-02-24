// Copyright (c) Microsoft Corporation. All rights reserved.
// StateManager.cs

using Orleans.Core;

namespace Microsoft.AutoGen.RuntimeGateway.Grpc;

/// <summary>
/// A helper class which wraps a grain state instance and ensures that only a single write operation is outstanding at any moment in time.
/// </summary>
/// <param name="state">The grain state.</param>
internal sealed class StateManager(IStorage state)
{
    /// <summary>
    /// Allows state writing to happen in the background.
    /// </summary>
    private Task? _pendingOperation;

    // When reentrant grain is doing WriteStateAsync, etag violations are possible due to concurrent writes.
    // The solution is to serialize and batch writes, and make sure only a single write is outstanding at any moment in time.
    public async ValueTask WriteStateAsync()
    {
        await PerformOperationAsync(static state => state.WriteStateAsync());
    }

    public async ValueTask ClearStateAsync()
    {
        await PerformOperationAsync(static state => state.ClearStateAsync());
    }

    public async ValueTask PerformOperationAsync(Func<IStorage, Task> performOperation)
    {
        if (_pendingOperation is Task currentWriteStateOperation)
        {
            // await the outstanding write, but ignore it since it doesn't include our changes
            await currentWriteStateOperation.ConfigureAwait(ConfigureAwaitOptions.SuppressThrowing | ConfigureAwaitOptions.ContinueOnCapturedContext);
            if (_pendingOperation == currentWriteStateOperation)
            {
                // only null out the outstanding operation if it's the same one as the one we awaited, otherwise
                // another request might have already done so.
                _pendingOperation = null;
            }
        }

        Task operation;
        if (_pendingOperation is null)
        {
            // If after the initial write is completed, no other request initiated a new write operation, do it now.
            operation = performOperation(state);
            _pendingOperation = operation;
        }
        else
        {
            // If there were many requests enqueued to persist state, there is no reason to enqueue a new write 
            // operation for each, since any write (after the initial one that we already awaited) will have cumulative
            // changes including the one requested by our caller. Just await the new outstanding write.
            operation = _pendingOperation;
        }

        try
        {
            await operation;
        }
        finally
        {
            if (_pendingOperation == operation)
            {
                // only null out the outstanding operation if it's the same one as the one we awaited, otherwise
                // another request might have already done so.
                _pendingOperation = null;
            }
        }
    }
}
