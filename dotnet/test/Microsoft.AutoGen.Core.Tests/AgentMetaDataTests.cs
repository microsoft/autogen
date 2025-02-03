// Copyright (c) Microsoft Corporation. All rights reserved.
// AgentMetaDataTests.cs
using FluentAssertions;
using Microsoft.AutoGen.Contracts;
using Xunit;

namespace Microsoft.AutoGen.Core.Tests;

[Trait("Category", "UnitV2")]
public class AgentMetadataTests()
{
    [Fact]
    public void AgentMetadataShouldInitializeCorrectlyTest()
    {
        var metadata = new AgentMetadata("TestType", "TestKey", "TestDescription");

        metadata.Type.Should().Be("TestType");
        metadata.Key.Should().Be("TestKey");
        metadata.Description.Should().Be("TestDescription");
    }
}
