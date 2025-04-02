// Copyright (c) Microsoft Corporation. All rights reserved.
// ISaveState.cs

using System.Text.Json;

namespace Microsoft.AutoGen.Contracts;

/// <summary>
/// Defines a contract for saving and loading the state of an object.
/// The state must be JSON serializable.
/// </summary>
public interface ISaveState
{
    public static ValueTask<JsonElement> DefaultSaveStateAsync() => new(JsonDocument.Parse("{}").RootElement);

    /// <summary>
    /// Saves the current state of the object.
    /// </summary>
    /// <returns>
    /// A task representing the asynchronous operation, returning a dictionary
    /// containing the saved state. The structure of the state is implementation-defined
    /// but must be JSON serializable.
    /// </returns>
    public virtual ValueTask<JsonElement> SaveStateAsync() => DefaultSaveStateAsync();

    /// <summary>
    /// Loads a previously saved state into the object.
    /// </summary>
    /// <param name="state">
    /// A dictionary representing the saved state. The structure of the state
    /// is implementation-defined but must be JSON serializable.
    /// </param>
    /// <returns>A task representing the asynchronous operation.</returns>
    public virtual ValueTask LoadStateAsync(JsonElement state) => ValueTask.CompletedTask;
}

