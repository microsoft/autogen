// Copyright (c) 2023 - 2024, Owners of https://github.com/autogenhub
// SPDX-License-Identifier: Apache-2.0
// Contributions to this project, i.e., https://github.com/autogenhub/autogen, 
// are licensed under the Apache License, Version 2.0 (Apache-2.0).
// Portions derived from  https://github.com/microsoft/autogen under the MIT License.
// SPDX-License-Identifier: MIT
// Copyright (c) Microsoft Corporation. All rights reserved.
// WorkflowTest.cs

using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using FluentAssertions;
using Xunit;

namespace AutoGen.Tests;

public class WorkflowTest
{
    [Fact]
    public async Task TransitionTestAsync()
    {
        var alice = new EchoAgent("alice");
        var bob = new EchoAgent("bob");

        var aliceToBob = Transition.Create(alice, bob, async (from, to, messages, _) =>
        {
            if (messages.Any(m => m.GetContent() == "Hello"))
            {
                return true;
            }

            return false;
        });

        var canTransit = await aliceToBob.CanTransitionAsync([]);
        canTransit.Should().BeFalse();

        canTransit = await aliceToBob.CanTransitionAsync([new TextMessage(Role.Assistant, "Hello")]);
        canTransit.Should().BeTrue();

        // if no function is provided, it should always return true
        var aliceToBobNoFunction = Transition.Create(alice, bob);
        canTransit = await aliceToBobNoFunction.CanTransitionAsync(new[] { new TextMessage(Role.Assistant, "Hello") });
        canTransit.Should().BeTrue();
    }

    [Fact]
    public async Task WorkflowBasicTestAsync()
    {
        var alice = new EchoAgent("alice");
        var bob = new EchoAgent("bob");
        var charlie = new EchoAgent("charlie");

        // alice can speak to bob
        // bob can speak to charlie
        // charlie can speak to alice

        var aliceToBob = Transition.Create(alice, bob);
        var bobToCharlie = Transition.Create(bob, charlie);
        var charlieToAlice = Transition.Create(charlie, alice);
        var workflow = new Graph([aliceToBob, bobToCharlie, charlieToAlice]);
        IAgent currentAgent = alice;
        var agentNames = new List<string>();
        do
        {
            agentNames.Add(currentAgent.Name!);
            var nextAgents = await workflow.TransitToNextAvailableAgentsAsync(currentAgent, []);
            nextAgents.Count().Should().Be(1);
            currentAgent = nextAgents.First();
        }
        while (currentAgent != alice);

        agentNames.Should().BeEquivalentTo(["alice", "bob", "charlie"]);
    }
}
