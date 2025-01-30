// Copyright (c) Microsoft Corporation. All rights reserved.
// AgentIdTests.cs
using FluentAssertions;
using Microsoft.AutoGen.Contracts;
using Xunit;

namespace Microsoft.AutoGen.Core.Tests;

public class AgentIdTests()
{
    [Fact]
    public void AgentIdShouldInitializeCorrectlyTest()
    {
        var agentId = new AgentId("TestType", "TestKey");

        agentId.Type.Should().Be("TestType");
        agentId.Key.Should().Be("TestKey");
    }

    [Fact]
    public void AgentIdShouldConvertFromTupleTest()
    {
        var agentTuple = ("TupleType", "TupleKey");
        var agentId = new AgentId(agentTuple);

        agentId.Type.Should().Be("TupleType");
        agentId.Key.Should().Be("TupleKey");
    }

    [Fact]
    public void AgentIdShouldParseFromStringTest()
    {
        var agentId = AgentId.FromStr("ParsedType/ParsedKey");

        agentId.Type.Should().Be("ParsedType");
        agentId.Key.Should().Be("ParsedKey");
    }

    [Fact]
    public void AgentIdShouldCompareEqualityCorrectlyTest()
    {
        var agentId1 = new AgentId("SameType", "SameKey");
        var agentId2 = new AgentId("SameType", "SameKey");
        var agentId3 = new AgentId("DifferentType", "DifferentKey");

        agentId1.Should().Be(agentId2);
        agentId1.Should().NotBe(agentId3);
        (agentId1 == agentId2).Should().BeTrue();
        (agentId1 != agentId3).Should().BeTrue();
    }

    [Fact]
    public void AgentIdShouldGenerateCorrectHashCodeTest()
    {
        var agentId1 = new AgentId("HashType", "HashKey");
        var agentId2 = new AgentId("HashType", "HashKey");
        var agentId3 = new AgentId("DifferentType", "DifferentKey");

        agentId1.GetHashCode().Should().Be(agentId2.GetHashCode());
        agentId1.GetHashCode().Should().NotBe(agentId3.GetHashCode());
    }
}
