// Copyright (c) Microsoft Corporation. All rights reserved.
// ISaveState.cs

using System.Text.Json;

namespace Microsoft.AutoGen.Contracts;

/// <summary>
/// Defines a contract for saving and loading the state of an object.
/// The state must be JSON serializable.
/// </summary>
/// <typeparam name="T">The type of the object implementing this interface.</typeparam>
public interface ISaveState<T>
{
    /// <summary>
    /// Saves the current state of the object.
    /// </summary>
    /// <returns>
    /// A task representing the asynchronous operation, returning a dictionary
    /// containing the saved state. The structure of the state is implementation-defined
    /// but must be JSON serializable.
    /// </returns>
    public ValueTask<JsonElement> SaveStateAsync();

    /// <summary>
    /// Loads a previously saved state into the object.
    /// </summary>
    /// <param name="state">
    /// A dictionary representing the saved state. The structure of the state
    /// is implementation-defined but must be JSON serializable.
    /// </param>
    /// <returns>A task representing the asynchronous operation.</returns>
    public ValueTask LoadStateAsync(JsonElement state);
}

