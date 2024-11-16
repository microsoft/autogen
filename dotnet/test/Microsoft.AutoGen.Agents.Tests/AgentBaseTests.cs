// Copyright (c) Microsoft Corporation. All rights reserved.
// AgentBaseTests.cs

using FluentAssertions;
using Google.Protobuf.Reflection;
using Microsoft.AutoGen.Abstractions;
using Microsoft.Extensions.Logging;
using Moq;
using Xunit;

namespace Microsoft.AutoGen.Agents.Tests;

public class AgentBaseTests
{
    [Fact]
    public async Task ItInvokeRightHandlerTestAsync()
    {
        var mockContext = new Mock<IAgentRuntime>();
        var agent = new TestAgent(mockContext.Object, new EventTypes(TypeRegistry.Empty, [], []), new Logger<AgentBase>(new LoggerFactory()));

        await agent.HandleObject("hello world");
        await agent.HandleObject(42);

        agent.ReceivedItems.Should().HaveCount(2);
        agent.ReceivedItems[0].Should().Be("hello world");
        agent.ReceivedItems[1].Should().Be(42);
    }

    /// <summary>
    /// The test agent is a simple agent that is used for testing purposes.
    /// </summary>
    public class TestAgent : AgentBase, IHandle<string>, IHandle<int>
    {
        public TestAgent(IAgentRuntime context, EventTypes eventTypes, Logger<AgentBase> logger) : base(context, eventTypes, logger)
        {
        }

        public Task Handle(string item)
        {
            ReceivedItems.Add(item);
            return Task.CompletedTask;
        }

        public Task Handle(int item)
        {
            ReceivedItems.Add(item);
            return Task.CompletedTask;
        }

        public List<object> ReceivedItems { get; private set; } = [];
    }
}
