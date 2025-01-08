// Copyright (c) Microsoft Corporation. All rights reserved.
// AgentMetadataTests.cs

using FluentAssertions;
using FluentAssertions.Execution;
using Tests.Events;
using Xunit;

namespace Microsoft.AutoGen.Core.Tests;

public class AgentMetadataTests
{
    [Fact]
    public void EventTypes_IsPopulated_From_Assembly()
    {
        var assembly = typeof(TestAgent).Assembly;
        var eventTypes = ReflectionHelper.GetAgentsMetadata(assembly);
        using var _=new AssertionScope();
        eventTypes.Should().NotBeNull();
        eventTypes.CheckIfTypeHandles(typeof(TestAgent), GoodBye.Descriptor.FullName).Should().BeTrue();
    }
}
