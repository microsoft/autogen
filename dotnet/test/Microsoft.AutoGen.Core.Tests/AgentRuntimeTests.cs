// Copyright (c) Microsoft Corporation. All rights reserved.
// AgentRuntimeTests.cs
using FluentAssertions;
using Microsoft.AutoGen.Contracts;
using Microsoft.Extensions.Logging;
using Xunit;

namespace Microsoft.AutoGen.Core.Tests;

[Trait("Category", "UnitV2")]
public class AgentRuntimeTests()
{
    [Fact]
    public async Task RuntimeAgentPublishToSelfTest()
    {
        var runtime = new InProcessRuntime();
        await runtime.StartAsync();

        Logger<BaseAgent> logger = new(new LoggerFactory());
        SubscribedSelfPublishAgent agent = null!;

        await runtime.RegisterAgentFactoryAsync("MyAgent", (id, runtime) =>
        {
            agent = new SubscribedSelfPublishAgent(id, runtime, logger);
            return ValueTask.FromResult(agent);
        });

        // Ensure the agent is actually created
        AgentId agentId = await runtime.GetAgentAsync("MyAgent", lazy: false);

        // Validate agent ID
        agentId.Should().Be(agent.Id, "Agent ID should match the registered agent");

        await runtime.RegisterImplicitAgentSubscriptionsAsync<SubscribedSelfPublishAgent>("MyAgent");

        var topicType = "TestTopic";

        await runtime.PublishMessageAsync(new TextMessage { Source = topicType, Content = "self_message" }, new TopicId(topicType)).ConfigureAwait(true);

        await runtime.RunUntilIdleAsync();

        agent.Text.Source.Should().Be("TestTopic");
        agent.Text.Content.Should().Be("self_message");
    }
}
