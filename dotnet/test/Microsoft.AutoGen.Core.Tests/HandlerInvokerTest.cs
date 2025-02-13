// Copyright (c) Microsoft Corporation. All rights reserved.
// HandlerInvokerTest.cs

using FluentAssertions;
using Microsoft.AutoGen.Contracts;
using Xunit;

namespace Microsoft.AutoGen.Core.Tests;

[Trait("Category", "UnitV2")]
public class HandlerInvokerTest()
{
    public List<(string, MessageContext)> PublishlikeInvocations = new List<(string, MessageContext)>();

    public ValueTask PublishlikeAsync(string message, MessageContext messageContext)
    {
        this.PublishlikeInvocations.Add((message, messageContext));
        return ValueTask.CompletedTask;
    }

    public List<(string, MessageContext)> SendlikeInvocations = new List<(string, MessageContext)>();

    public ValueTask<int> SendlikeAsync(string message, MessageContext messageContext)
    {
        this.SendlikeInvocations.Add((message, messageContext));
        return ValueTask.FromResult(this.SendlikeInvocations.Count);
    }

    [Fact]
    public async Task Test_InvokingPublishlike_Succeeds()
    {
        MessageContext messageContext = new MessageContext(Guid.NewGuid().ToString(), CancellationToken.None);

        var methodInfo = typeof(HandlerInvokerTest).GetMethod(nameof(PublishlikeAsync))!;
        var invoker = new HandlerInvoker(methodInfo, this);

        object? result = await invoker.InvokeAsync("Hello, world!", messageContext);

        this.PublishlikeInvocations.Should().HaveCount(1);
        this.PublishlikeInvocations[0].Item1.Should().Be("Hello, world!");
        result.Should().BeNull();
    }

    [Fact]
    public async Task Test_InvokingSendlike_Succeeds()
    {
        MessageContext messageContext = new MessageContext(Guid.NewGuid().ToString(), CancellationToken.None);

        var methodInfo = typeof(HandlerInvokerTest).GetMethod(nameof(SendlikeAsync))!;
        var invoker = new HandlerInvoker(methodInfo, this);

        object? result = await invoker.InvokeAsync("Hello, world!", messageContext);

        this.SendlikeInvocations.Should().HaveCount(1);
        this.SendlikeInvocations[0].Item1.Should().Be("Hello, world!");
        result.Should().Be(1);
    }
}
