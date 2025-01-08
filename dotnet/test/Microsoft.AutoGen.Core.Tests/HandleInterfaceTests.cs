// Copyright (c) Microsoft Corporation. All rights reserved.
// HandleInterfaceTests.cs

using FluentAssertions;
using Tests.Events;
using Xunit;

namespace Microsoft.AutoGen.Core.Tests;

public class HandleInterfaceTests
{
    [Fact]
    public void Can_Get_Handler_Methods_From_Class()
    {
        var source = typeof(TestAgent);
        var handlers =  source.GetHandlers();

        handlers.Should().NotBeNullOrEmpty();
    }

    [Fact]
    public void Handlers_Supports_Cancellation()
    {
        var source = typeof(TestAgent);
        var handlers = source.GetHandlers();

        handlers.Should().AllSatisfy(handler =>
            handler.GetParameters().Should().ContainSingle(p => p.ParameterType == typeof(CancellationToken))
        );
    }

    [Fact]
    public void Can_Build_Handlers_Lookup()
    {
        var source = typeof(TestAgent);
        var handlers = source.GetHandlersLookupTable();

        handlers.Should().ContainKey(typeof(GoodBye));
    }
}
