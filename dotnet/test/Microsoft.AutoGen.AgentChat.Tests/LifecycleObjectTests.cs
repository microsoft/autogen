// Copyright (c) Microsoft Corporation. All rights reserved.
// LifecycleObjectTests.cs

using FluentAssertions;
using Microsoft.AutoGen.AgentChat.GroupChat;
using Xunit;

namespace Microsoft.AutoGen.AgentChat.Tests;

internal sealed class LifecycleObjectFixture : LifecycleObject
{
    public enum LifecycleState
    {
        Deinitialized,
        Initialized
    }

    public LifecycleState State { get; private set; }

    public Func<ValueTask> DeinitializeOverride { get; set; } = () => ValueTask.CompletedTask;
    public Func<ValueTask> InitializeOverride { get; set; } = () => ValueTask.CompletedTask;

    public Action InitializeErrorOverride { get; set; }
    public Action DeinitializeErrorOverride { get; set; }

    private int initializeCallCount;
    private int deinitializeCallCount;
    private int initializeErrorCount;
    private int deinitializeErrorCount;

    public int InitializeCallCount => this.initializeCallCount;
    public int DeinitializeCallCount => this.deinitializeCallCount;
    public int InitializeErrorCount => this.initializeErrorCount;
    public int DeinitializeErrorCount => this.deinitializeErrorCount;

    public LifecycleObjectFixture()
    {
        this.State = LifecycleState.Deinitialized;

        this.InitializeErrorOverride = base.OnInitializeError;
        this.DeinitializeErrorOverride = base.OnDeinitializeError;
    }

    protected override void OnInitializeError()
    {
        Interlocked.Increment(ref this.initializeErrorCount);

        this.InitializeErrorOverride();
    }

    protected override void OnDeinitializeError()
    {
        Interlocked.Increment(ref this.deinitializeErrorCount);

        this.DeinitializeErrorOverride();
    }

    protected sealed override ValueTask DeinitializeCore()
    {
        Interlocked.Increment(ref this.deinitializeCallCount);
        this.State = LifecycleState.Deinitialized;

        return DeinitializeOverride();
    }

    protected sealed override ValueTask InitializeCore()
    {
        Interlocked.Increment(ref this.initializeCallCount);
        this.State = LifecycleState.Initialized;

        return InitializeOverride();
    }
}

[Trait("Category", "UnitV2")]
public class LifecycleObjectTests
{
    /*
     We should be testing the following conditions:
        - SmokeTest: Happy path: Initialize, Deinitialize, Initialize, Deinitialize, validate states and call counts
        - Error handling: Initialize, Initialize; Deinitialize; Initialize, Deinitialize, Deinitialize
     */

    [Fact]
    public async Task InitializeAndDeinitialize_SucceedsTwice()
    {
        // Arrange
        LifecycleObjectFixture fixture = new();

        // Validate preconditions
        fixture.State.Should().Be(LifecycleObjectFixture.LifecycleState.Deinitialized, "LifecycleObject should be in Deinitialized state initially");
        fixture.InitializeCallCount.Should().Be(0, "Initialize should not have been called yet");
        fixture.DeinitializeCallCount.Should().Be(0, "Deinitialize should not have been called yet");
        fixture.InitializeErrorCount.Should().Be(0, "there should be no initialization errors");
        fixture.DeinitializeErrorCount.Should().Be(0, "there should be no deinitialization errors");

        // Act
        await fixture.InitializeAsync();

        // Validate postconditions 1
        fixture.State.Should().Be(LifecycleObjectFixture.LifecycleState.Initialized, "LifecycleObject should be in Initialized state after Initialize");
        fixture.InitializeCallCount.Should().Be(1, "Initialize should have been called once");
        fixture.DeinitializeCallCount.Should().Be(0, "Deinitialize should not have been called yet");
        fixture.InitializeErrorCount.Should().Be(0, "there should be no initialization errors");
        fixture.DeinitializeErrorCount.Should().Be(0, "there should be no deinitialization errors");

        // Act 2
        await fixture.DeinitializeAsync();

        // Validate postconditions 2
        fixture.State.Should().Be(LifecycleObjectFixture.LifecycleState.Deinitialized, "LifecycleObject should be in Deinitialized state after Deinitialize");
        fixture.InitializeCallCount.Should().Be(1, "Initialize should have been called once");
        fixture.DeinitializeCallCount.Should().Be(1, "Deinitialize should have been called once");
        fixture.InitializeErrorCount.Should().Be(0, "there should be no initialization errors");
        fixture.DeinitializeErrorCount.Should().Be(0, "there should be no deinitialization errors");

        // Act 3

        await fixture.InitializeAsync();

        // Validate postconditions 3

        fixture.State.Should().Be(LifecycleObjectFixture.LifecycleState.Initialized, "LifecycleObject should be in Initialized state after Initialize");
        fixture.InitializeCallCount.Should().Be(2, "Initialize should have been called twice");
        fixture.DeinitializeCallCount.Should().Be(1, "Deinitialize should have been called once");
        fixture.InitializeErrorCount.Should().Be(0, "there should be no initialization errors");
        fixture.DeinitializeErrorCount.Should().Be(0, "there should be no deinitialization errors");

        // Act 4

        await fixture.DeinitializeAsync();

        // Validate postconditions 4

        fixture.State.Should().Be(LifecycleObjectFixture.LifecycleState.Deinitialized, "LifecycleObject should be in Deinitialized state after Deinitialize");
        fixture.InitializeCallCount.Should().Be(2, "Initialize should have been called twice");
        fixture.DeinitializeCallCount.Should().Be(2, "Deinitialize should have been called twice");
        fixture.InitializeErrorCount.Should().Be(0, "there should be no initialization errors");
        fixture.DeinitializeErrorCount.Should().Be(0, "there should be no deinitialization errors");
    }

    [Fact]
    public async Task Initialize_FailsWhenInitialized()
    {
        // Testing two things: We should expect InvalidOperationException by default, and that we called into the override

        // Arrange
        LifecycleObjectFixture fixture = new();
        await fixture.InitializeAsync();

        // Act
        Func<Task> secondInitialization = async () => await fixture.InitializeAsync();

        // Assert
        await secondInitialization.Should().ThrowAsync<InvalidOperationException>("LifecycleObject.InitializeAsync should throw InvalidOperationException when initialized");

        fixture.InitializeCallCount.Should().Be(1, "Initialize should have been called once successfully");
        fixture.InitializeErrorCount.Should().Be(1, "there should be one initialization error");
        fixture.DeinitializeCallCount.Should().Be(0, "Deinitialize should not have been called yet");
        fixture.DeinitializeErrorCount.Should().Be(0, "there should be no deinitialization errors");
    }

    [Fact]
    public async Task Deinitialize_FailsWhenNotInitialized()
    {
        // Arrange
        LifecycleObjectFixture fixture = new();

        // Act
        Func<Task> deinitialization = async () => await fixture.DeinitializeAsync();

        // Assert
        await deinitialization.Should().ThrowAsync<InvalidOperationException>("LifecycleObject.DeinitializeAsync should throw InvalidOperationException when not initialized");

        fixture.InitializeCallCount.Should().Be(0, "Initialize should not have been called yet");
        fixture.InitializeErrorCount.Should().Be(0, "there should be no initialization errors");
        fixture.DeinitializeCallCount.Should().Be(0, "Deinitialize should not have been called successfully yet");
        fixture.DeinitializeErrorCount.Should().Be(1, "there should be one deinitialization error");

        // Act 2
        await fixture.InitializeAsync();
        await fixture.DeinitializeAsync();

        Func<Task> secondDeinitialization = async () => await fixture.DeinitializeAsync();

        // Assert 2
        await secondDeinitialization.Should().ThrowAsync<InvalidOperationException>("LifecycleObject.DeinitializeAsync should throw InvalidOperationException when not initialized");

        fixture.InitializeCallCount.Should().Be(1, "Initialize should have been called once successfully");
        fixture.InitializeErrorCount.Should().Be(0, "there should be no initialization errors");
        fixture.DeinitializeCallCount.Should().Be(1, "Deinitialize should have been called successfully once");
        fixture.DeinitializeErrorCount.Should().Be(2, "there should be two deinitialization errors");
    }
}
