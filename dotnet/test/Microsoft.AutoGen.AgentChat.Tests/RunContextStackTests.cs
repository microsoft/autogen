// Copyright (c) Microsoft Corporation. All rights reserved.
// RunContextStackTests.cs

using FluentAssertions;
using Microsoft.AutoGen.AgentChat.GroupChat;
using Moq;
using Xunit;

namespace Microsoft.AutoGen.AgentChat.Tests;

public class RunContextStackTests
{
    public static IRunContextLayer CreateLayer(Action<Mock<IRunContextLayer>>? setupAction = null)
    {
        Mock<IRunContextLayer> layer = new();

        if (setupAction != null)
        {
            setupAction(layer);
        }
        else
        {
            layer.Setup(l => l.InitializeAsync()).Returns(ValueTask.CompletedTask);
            layer.Setup(l => l.DeinitializeAsync()).Returns(ValueTask.CompletedTask);
        }

        return layer.Object;
    }

    [Fact]
    public async Task Initialize_SucceedsWithNoLayers()
    {
        // Arrange
        RunContextStack stack = new RunContextStack();

        // Act
        Func<Task> func = async () => await stack.InitializeAsync();

        // Assert
        await func.Should().NotThrowAsync("RunContextStack should work without context frames");
    }

    [Fact]
    public async Task Deinitialize_SucceedsWithNoLayers()
    {
        // Arrange
        RunContextStack stack = new RunContextStack();
        await stack.InitializeAsync();

        // Act
        Func<Task> func = async () => await stack.DeinitializeAsync();

        // Assert
        await func.Should().NotThrowAsync("RunContextStack should work without context frames");
    }

    [Fact]
    public async Task PushLayer_FailsWhenInitialized()
    {
        // Arrange
        RunContextStack stack = new RunContextStack();
        await stack.InitializeAsync();

        // Act
        Action pushLayerAction = () => stack.PushLayer(CreateLayer());

        // Assert
        pushLayerAction.Should().Throw<InvalidOperationException>("RunContextStack should not allow pushing layers when initialized");
    }

    [Fact]
    public async Task PopLayer_FailsWhenInitialized()
    {
        // Arrange
        RunContextStack stack = new RunContextStack();
        await stack.InitializeAsync();

        // Act
        Action popLayerAction = stack.PopLayer;

        // Assert
        popLayerAction.Should().Throw<InvalidOperationException>("RunContextStack should not allow popping layers when initialized");
    }

    [Fact]
    public Task InitializeDeinitialize_ShouldInvokeLayersInOrder_WhenPushed()
    {
        return PrepareAndRun_LayerOrderTest(Arrange);

        static RunContextStack Arrange(IEnumerable<IRunContextLayer> layers)
        {
            RunContextStack stack = new RunContextStack();

            foreach (IRunContextLayer layer in layers)
            {
                stack.PushLayer(layer);
            }

            return stack;
        }
    }

    [Fact]
    public Task InitializeDeinitialize_ShouldInvokeLayersInOrder_WhenConstructed()
    {
        return PrepareAndRun_LayerOrderTest(Arrange);

        static RunContextStack Arrange(IEnumerable<IRunContextLayer> layers)
        {
            return new RunContextStack([.. layers]);
        }
    }

    private async Task PrepareAndRun_LayerOrderTest(Func<IEnumerable<IRunContextLayer>, RunContextStack> arrangeStack)
    {
        bool bottomLayerInit = false;
        bool bottomLayerDeinit = false;

        bool topLayerInit = false;
        bool topLayerDeinit = false;

        // Arrange
        IRunContextLayer topLayer = CreateLayer(mock =>
        {
            mock.Setup(l => l.InitializeAsync()).Callback(
                () =>
                {
                    topLayerInit.Should().BeFalse("Top Layer should not have been initialized yet");
                    bottomLayerInit.Should().BeFalse("Bottom Layer should not have been initialized yet");

                    topLayerInit = true;
                }
                ).Returns(ValueTask.CompletedTask).Verifiable();
            mock.Setup(l => l.DeinitializeAsync()).Callback(
                () =>
                {
                    topLayerInit.Should().BeTrue("Top Layer should have been initialized");
                    bottomLayerInit.Should().BeTrue("Bottom Layer should have been initialized");

                    bottomLayerDeinit.Should().BeTrue("Bottom Layer should be deinitialized before Top Layer");
                    topLayerDeinit.Should().BeFalse("Top Layer should not have been deinitialized yet");

                    topLayerDeinit = true;
                }).Returns(ValueTask.CompletedTask).Verifiable();
        });

        IRunContextLayer bottomLayer = CreateLayer(mock =>
        {
            mock.Setup(l => l.InitializeAsync()).Callback(
                () =>
                {
                    topLayerInit.Should().BeTrue("Top Layer should have been initialized before Bottom Layer");
                    bottomLayerInit.Should().BeFalse("Bottom Layer should not have been initialized yet");

                    bottomLayerInit = true;
                }
                ).Returns(ValueTask.CompletedTask).Verifiable();
            mock.Setup(l => l.DeinitializeAsync()).Callback(
                () =>
                {
                    topLayerInit.Should().BeTrue("Top Layer should have been initialized");
                    bottomLayerInit.Should().BeTrue("Bottom Layer should have been initialized");

                    bottomLayerDeinit.Should().BeFalse("Bottom Layer should not have been deinitialized yet");
                    topLayerDeinit.Should().BeFalse("Top Layer should not have been deinitialized yet");

                    bottomLayerDeinit = true;
                }).Returns(ValueTask.CompletedTask).Verifiable();
        });

        RunContextStack stack = arrangeStack([bottomLayer, topLayer]);

        // Act
        await stack.InitializeAsync();

        // Assert
        Mock.Get(topLayer).Verify(l => l.InitializeAsync(), Times.Once);
        Mock.Get(bottomLayer).Verify(l => l.InitializeAsync(), Times.Once);

        bottomLayerInit.Should().BeTrue("Top Layer should have been initialized");
        topLayerInit.Should().BeTrue("Bottom Layer should have been initialized");

        // Act 2
        await stack.DeinitializeAsync();

        // Assert 2
        Mock.Get(bottomLayer).Verify(l => l.DeinitializeAsync(), Times.Once);
        Mock.Get(topLayer).Verify(l => l.DeinitializeAsync(), Times.Once);

        topLayerDeinit.Should().BeTrue("Bottom Layer should have been deinitialized");
        bottomLayerDeinit.Should().BeTrue("Top Layer should have been deinitialized");
    }

    [Fact]
    public async Task CreateOverrides_GetsInvokedOnError()
    {
        int initializeErrors = 0;
        int deinitializeErrors = 0;

        // Arrange
        IRunContextLayer overrides = RunContextStack.OverrideErrors(
            initializeError: () => initializeErrors++,
            deinitializeError: () => deinitializeErrors++);

        RunContextStack stack = new RunContextStack(overrides);

        // Act
        Func<Task> deinitializeAction = async () => await stack.DeinitializeAsync();

        // Assert
        // The first Deinitialize should throw because we only override after the top layer it initialized
        await deinitializeAction.Should().ThrowAsync<InvalidOperationException>("Deinitialize should throw an exception");

        // Act 2
        await stack.InitializeAsync();
        Func<Task> initializeAgainAction = async () => await stack.InitializeAsync();

        // Assert 2
        // The second Initialize should not throw, because the overrides should be applied
        await initializeAgainAction.Should().NotThrowAsync("Initialize should not throw an exception");

        initializeErrors.Should().Be(1, "There should be one initialization error");
        deinitializeErrors.Should().Be(0, "There should not have been an overriden invocation of a deinitialize error.");
    }

    [Fact]
    public async Task Enter_DisposableWorksIdempotently()
    {
        int initializeCount = 0;
        int deinitializeCount = 0;

        // Arrange
        IRunContextLayer layer = CreateLayer(mock =>
        {
            mock.Setup(l => l.InitializeAsync()).Callback(() => initializeCount++).Returns(ValueTask.CompletedTask);
            mock.Setup(l => l.DeinitializeAsync()).Callback(() => deinitializeCount++).Returns(ValueTask.CompletedTask);
        });

        RunContextStack stack = new RunContextStack(layer);

        // Act
        IAsyncDisposable exitDisposable = await stack.Enter();

        // Assert
        initializeCount.Should().Be(1, "Layer should have been initialized once");
        deinitializeCount.Should().Be(0, "Layer should not have been deinitialized yet");

        // Act 2
        await exitDisposable.DisposeAsync();

        // Assert 2
        initializeCount.Should().Be(1, "Layer should have been initialized once");
        deinitializeCount.Should().Be(1, "Layer should have been deinitialized once");

        // Act 3
        Func<Task> disposeAgain = async () => await exitDisposable.DisposeAsync();

        // Assert 3
        await disposeAgain.Should().NotThrowAsync("Dispose should be idempotent");

        initializeCount.Should().Be(1, "Layer should have been initialized once");
        deinitializeCount.Should().Be(1, "Layer should have been deinitialized once");
    }
}
