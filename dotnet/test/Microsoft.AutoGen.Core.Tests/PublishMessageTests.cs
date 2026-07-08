// Copyright (c) Microsoft Corporation. All rights reserved.
// PublishMessageTests.cs

using System.Reflection;
using FluentAssertions;
using Microsoft.AutoGen.Contracts;
using Microsoft.Extensions.Logging;
using Xunit;

namespace Microsoft.AutoGen.Core.Tests;

public static class PublishTestsExtensions
{
    public static async ValueTask RegisterReceiverAgent(this MessagingTestFixture fixture,
        string? agentNameSuffix = null,
        params string[] topicTypes)
    {
        await fixture.RegisterFactoryMapInstances($"{nameof(ReceiverAgent)}{agentNameSuffix ?? string.Empty}",
            (id, runtime) => ValueTask.FromResult(new ReceiverAgent(id, runtime, string.Empty)));

        foreach (string topicType in topicTypes)
        {
            await fixture.Runtime.AddSubscriptionAsync(new TypeSubscription(topicType, $"{nameof(ReceiverAgent)}{agentNameSuffix ?? string.Empty}"));
        }
    }

    public static async ValueTask RegisterErrorAgent(this MessagingTestFixture fixture,
        string? agentNameSuffix = null,
        params string[] topicTypes)
    {
        await fixture.RegisterFactoryMapInstances($"{nameof(ErrorAgent)}{agentNameSuffix ?? string.Empty}",
            (id, runtime) => ValueTask.FromResult(new ErrorAgent(id, runtime, string.Empty)));

        foreach (string topicType in topicTypes)
        {
            await fixture.Runtime.AddSubscriptionAsync(new TypeSubscription(topicType, $"{nameof(ErrorAgent)}{agentNameSuffix ?? string.Empty}"));
        }
    }
}

[Trait("Category", "UnitV2")]
public class PublishMessageTests
{
    private sealed class PublisherAgent : BaseAgent, IHandle<BasicMessage>
    {
        private IList<TopicId> targetTopics;

        public PublisherAgent(AgentId id, IAgentRuntime runtime, string description, IList<TopicId> targetTopics, ILogger<BaseAgent>? logger = null)
            : base(id, runtime, description, logger)
        {
            this.targetTopics = targetTopics;
        }

        public async ValueTask HandleAsync(BasicMessage item, MessageContext messageContext)
        {
            foreach (TopicId targetTopic in targetTopics)
            {
                BasicMessage message = new BasicMessage { Content = $"@{targetTopic}: {item.Content}" };
                await this.Runtime.PublishMessageAsync(message, targetTopic);
            }
        }
    }

    [Fact]
    public async Task Test_PublishMessage_Success()
    {
        MessagingTestFixture fixture = new MessagingTestFixture();

        await fixture.RegisterReceiverAgent(topicTypes: "TestTopic");
        await fixture.RegisterReceiverAgent("2", topicTypes: "TestTopic");

        await fixture.RunPublishTestAsync(new TopicId("TestTopic"), new BasicMessage { Content = "1" });

        fixture.GetAgentInstances<ReceiverAgent>().Values
            .Should().HaveCount(2, "Two agents should have been created")
                 .And.AllSatisfy(receiverAgent => receiverAgent.Messages
                                                               .Should().NotBeNull()
                                                                    .And.HaveCount(1)
                                                                    .And.ContainSingle(m => m.Content == "1"));
    }

    [Fact]
    public async Task Test_PublishMessage_SingleFailure()
    {
        MessagingTestFixture fixture = new MessagingTestFixture();

        await fixture.RegisterErrorAgent(topicTypes: "TestTopic");

        Func<Task> publishTask = async () => await fixture.RunPublishTestAsync(new TopicId("TestTopic"), new BasicMessage { Content = "1" });

        // Test that we wrap single errors appropriately
        (await publishTask.Should().ThrowAsync<AggregateException>())
                                   .Which.Should().Match<AggregateException>(
                                        ex => ex.InnerExceptions.Count == 1 &&
                                              ex.InnerExceptions.All(
                                                inEx => inEx is TargetInvocationException &&
                                                ((TargetInvocationException)inEx).InnerException is TestException));

        fixture.GetAgentInstances<ErrorAgent>().Values.Should().ContainSingle()
                                                .Which.DidThrow.Should().BeTrue("Agent should have thrown an exception");
    }

    [Fact]
    public async Task Test_PublishMessage_MultipleFailures()
    {
        MessagingTestFixture fixture = new MessagingTestFixture();

        await fixture.RegisterErrorAgent(topicTypes: "TestTopic");
        await fixture.RegisterErrorAgent("2", topicTypes: "TestTopic");

        Func<Task> publishTask = async () => await fixture.RunPublishTestAsync(new TopicId("TestTopic"), new BasicMessage { Content = "1" });

        // What we are really testing here is that a single exception does not prevent sending to the remaining agents
        (await publishTask.Should().ThrowAsync<AggregateException>())
                                   .Which.Should().Match<AggregateException>(
                                        ex => ex.InnerExceptions.Count == 2 &&
                                              ex.InnerExceptions.All(
                                                inEx => inEx is TargetInvocationException &&
                                                ((TargetInvocationException)inEx).InnerException is TestException));

        fixture.GetAgentInstances<ErrorAgent>().Values
            .Should().HaveCount(2)
                 .And.AllSatisfy(
                    agent => agent.DidThrow.Should().BeTrue("Agent should have thrown an exception"));
    }

    [Fact]
    public async Task Test_PublishMessage_MixedSuccessFailure()
    {
        MessagingTestFixture fixture = new MessagingTestFixture();

        await fixture.RegisterReceiverAgent(topicTypes: "TestTopic");
        await fixture.RegisterReceiverAgent("2", topicTypes: "TestTopic");

        await fixture.RegisterErrorAgent(topicTypes: "TestTopic");
        await fixture.RegisterErrorAgent("2", topicTypes: "TestTopic");

        Func<Task> publicTask = async () => await fixture.RunPublishTestAsync(new TopicId("TestTopic"), new BasicMessage { Content = "1" });

        // What we are really testing here is that raising exceptions does not prevent sending to the remaining agents
        (await publicTask.Should().ThrowAsync<AggregateException>())
                                   .Which.Should().Match<AggregateException>(
                                        ex => ex.InnerExceptions.Count == 2 &&
                                              ex.InnerExceptions.All(
                                                inEx => inEx is TargetInvocationException &&
                                                ((TargetInvocationException)inEx).InnerException is TestException));

        fixture.GetAgentInstances<ReceiverAgent>().Values
            .Should().HaveCount(2, "Two ReceiverAgents should have been created")
                 .And.AllSatisfy(receiverAgent => receiverAgent.Messages
                                                               .Should().NotBeNull()
                                                                    .And.HaveCount(1)
                                                                    .And.ContainSingle(m => m.Content == "1"),
                                 "ReceiverAgents should get published message regardless of ErrorAgents throwing exception.");

        fixture.GetAgentInstances<ErrorAgent>().Values
            .Should().HaveCount(2, "Two ErrorAgents should have been created")
                 .And.AllSatisfy(agent => agent.DidThrow.Should().BeTrue("ErrorAgent should have thrown an exception"));
    }

    [Fact]
    public async Task Test_PublishMessage_RecurrentPublishSucceeds()
    {
        MessagingTestFixture fixture = new MessagingTestFixture();

        await fixture.RegisterFactoryMapInstances(nameof(PublisherAgent),
            (id, runtime) => ValueTask.FromResult(new PublisherAgent(id, runtime, string.Empty, new List<TopicId> { new TopicId("TestTopic") })));

        await fixture.Runtime.AddSubscriptionAsync(new TypeSubscription("RunTest", nameof(PublisherAgent)));

        await fixture.RegisterReceiverAgent(topicTypes: "TestTopic");
        await fixture.RegisterReceiverAgent("2", topicTypes: "TestTopic");

        await fixture.RunPublishTestAsync(new TopicId("RunTest"), new BasicMessage { Content = "1" });

        TopicId testTopicId = new TopicId("TestTopic");
        fixture.GetAgentInstances<ReceiverAgent>().Values
            .Should().HaveCount(2, "Two ReceiverAgents should have been created")
                 .And.AllSatisfy(receiverAgent => receiverAgent.Messages
                                                               .Should().NotBeNull()
                                                                    .And.HaveCount(1)
                                                                    .And.ContainSingle(m => m.Content == $"@{testTopicId}: 1"));
    }
}
