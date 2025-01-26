// Copyright (c) Microsoft Corporation. All rights reserved.
// RegsitryStorage.cs

using System.Collections.Concurrent;
using System.Text.Json;
using Microsoft.AutoGen.Contracts;
using Microsoft.Extensions.Logging;

namespace Microsoft.AutoGen.Core;
/// <summary>
/// Storage implementation for the RegistryState
/// Note: if you really care about the performance and resilience of this you should probably use the distributed runtime and persistent storage through Orleans 
/// </summary>
public class RegistryStorage(ILogger<IRegistryStorage> logger) : IRegistryStorage
{
    /// a property representing the file path to the state file read from configuration
    public string FilePath { get; set; } = Environment.GetEnvironmentVariable("AGENTS_REGISTRY") ?? "registry.json";
    protected internal ILogger<IRegistryStorage> _logger = logger;

    public Task<AgentsRegistryState> ReadStateAsync(CancellationToken cancellationToken = default)
    {
        string json;
        var state = new AgentsRegistryState();
        if (File.Exists(FilePath)) { json = File.ReadAllText(FilePath); }
        else { 
            _logger.LogWarning("Registry file {FilePath} does not exist, starting with an empty Registry", FilePath);
            state.ETag = Guid.NewGuid().ToString();
            return new Task<AgentsRegistryState>(() => state);
        }
        try
        {
            state = JsonSerializer.Deserialize<AgentsRegistryState>(json) ?? new AgentsRegistryState();
        }
        catch (Exception e)
        {
            _logger.LogWarning(e, "Failed to read the Registry from {FilePath}, starting with an empty Registry", FilePath);
            state.ETag = Guid.NewGuid().ToString();
        }
        return new Task<AgentsRegistryState>(() => state);
    }

    public async ValueTask<string> WriteStateAsync(AgentsRegistryState state, CancellationToken cancellationToken = default)
    {
        // etags for optimistic concurrency control
        // if the Etag is null, its a new state
        // if the passed etag is null or empty, we should not check the current state's Etag - caller doesnt care
        // if both etags are set, they should match or it means that the state has changed since the last read. 
        if (string.IsNullOrEmpty(state.Etag) || (string.IsNullOrEmpty(eTag)) || (string.Equals(state.Etag, eTag, StringComparison.Ordinal)))
        {
            state.Etag = Guid.NewGuid().ToString();
            // serialize to JSON and write to file
            var json = JsonSerializer.Serialize(state);
            await File.WriteAllTextAsync(FilePath, json).ConfigureAwait(false);
        }
        else
        {
            //TODO - this is probably not the correct behavior to just throw - I presume we want to somehow let the caller know that the state has changed and they need to re-read it
            throw new ArgumentException(
                "The provided ETag does not match the current ETag. The state has been modified by another request.");
        }
        return state.Etag;
    }
}