// Copyright (c) Microsoft Corporation. All rights reserved.
// GraphTests.cs

using Xunit;

namespace AutoGen.Tests;

public class GraphTests
{
    [Fact]
    public void GraphTest()
    {
        var graph1 = new Graph();
        Assert.NotNull(graph1);

        var graph2 = new Graph(null);
        Assert.NotNull(graph2);
    }
}
