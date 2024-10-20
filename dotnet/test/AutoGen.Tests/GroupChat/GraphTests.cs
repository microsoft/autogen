// Copyright (c) 2023 - 2024, Owners of https://github.com/autogenhub
// SPDX-License-Identifier: Apache-2.0
// Contributions to this project, i.e., https://github.com/autogenhub/autogen, 
// are licensed under the Apache License, Version 2.0 (Apache-2.0).
// Portions derived from  https://github.com/microsoft/autogen under the MIT License.
// SPDX-License-Identifier: MIT
// Copyright (c) Microsoft Corporation. All rights reserved.
// GraphTests.cs

using Xunit;

namespace AutoGen.Tests
{
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
}
