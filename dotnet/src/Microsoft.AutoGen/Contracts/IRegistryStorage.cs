// Copyright (c) Microsoft Corporation. All rights reserved.
// IRegistryStorage.cs

namespace Microsoft.AutoGen.Contracts;

public interface IRegistryStorage
{
    /// <summary>
    /// Populates the Registry state from the storage.
    /// </summary>
    /// <param name="cancellationToken"></param>
    Task<AgentsRegistryState> ReadStateAsync(CancellationToken cancellationToken = default);
    /// <summary>
    /// Writes the Registry state to the storage.
    /// </summary>
    /// <param name="state"></param>
    /// <param name="cancellationToken"></param>
    /// <returns>the etag that was written</returns>
    ValueTask<string> WriteStateAsync(AgentsRegistryState state, CancellationToken cancellationToken = default);
}
