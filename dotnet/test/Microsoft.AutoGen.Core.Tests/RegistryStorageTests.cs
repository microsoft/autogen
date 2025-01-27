// Copyright (c) Microsoft Corporation. All rights reserved.
// RegistryStorageTests.cs
using System.Collections.Concurrent;
using System.Text.Json;
using Microsoft.AutoGen.Contracts;
using Microsoft.Extensions.Logging;
using Moq;
using Xunit;

namespace Microsoft.AutoGen.Core.Tests;

public class RegistryStorageTests
{
    private readonly Mock<ILogger<IRegistryStorage>> _loggerMock;
    private readonly RegistryStorage _registryStorage;

    public RegistryStorageTests()
    {
        _loggerMock = new Mock<ILogger<IRegistryStorage>>();
        _registryStorage = new RegistryStorage(_loggerMock.Object)
        {
            FilePath = "test_registry.json"
        };
    }

    [Fact]
    public async Task ReadStateAsync_ShouldReturnEmptyState_WhenFileDoesNotExist()
    {
        // Arrange
        if (File.Exists(_registryStorage.FilePath))
        {
            File.Delete(_registryStorage.FilePath);
        }

        // Act
        var state = await _registryStorage.ReadStateAsync();

        // Assert
        Assert.NotNull(state);
        Assert.Empty(state.AgentTypes);
    }

    [Fact]
    public async Task ReadStateAsync_ShouldReturnState_WhenFileExists()
    {
        // Arrange
        if (File.Exists(_registryStorage.FilePath))
        {
            File.Delete(_registryStorage.FilePath);
        }
        var agentType = "agent1";
        var expectedState = new AgentsRegistryState
        {
            Etag = Guid.NewGuid().ToString(),
            AgentTypes = new ConcurrentDictionary<string, AgentId>
            {
                [agentType] = new AgentId() { Type = agentType, Key = Guid.NewGuid().ToString() }
            }
        };
        var json = JsonSerializer.Serialize(expectedState);
        await File.WriteAllTextAsync(_registryStorage.FilePath, json);

        // Act
        var state = await _registryStorage.ReadStateAsync();

        // Assert
        Assert.NotNull(state);
        Assert.Single(state.AgentTypes);
        Assert.Equal(agentType, state.AgentTypes.Keys.First());
    }

    [Fact]
    public async Task WriteStateAsync_ShouldWriteStateToFile()
    {
        // Arrange
        if (File.Exists(_registryStorage.FilePath))
        {
            File.Delete(_registryStorage.FilePath);
        }
        var agentType = "agent1";
        var state = await _registryStorage.ReadStateAsync();
        state.AgentTypes.TryAdd(agentType, new AgentId() { Type = agentType, Key = Guid.NewGuid().ToString() });

        // Act
        await _registryStorage.WriteStateAsync(state);

        // Assert
        var json = await File.ReadAllTextAsync(_registryStorage.FilePath);
        var writtenState = JsonSerializer.Deserialize<AgentsRegistryState>(json);
        Assert.NotNull(writtenState);
        Assert.Single(writtenState.AgentTypes);
        Assert.Equal(agentType, writtenState.AgentTypes.Keys.First());
    }

    [Fact]
    public async Task WriteStateAsync_ShouldThrowException_WhenETagMismatch()
    {
        // Arrange
        // Arrange
        if (File.Exists(_registryStorage.FilePath))
        {
            File.Delete(_registryStorage.FilePath);
        }
        var initialState = await _registryStorage.ReadStateAsync();

        var newState = new AgentsRegistryState { Etag = "mismatch" };

        // Act & Assert
        await Assert.ThrowsAsync<ArgumentException>(async () => await _registryStorage.WriteStateAsync(newState));
    }
}
