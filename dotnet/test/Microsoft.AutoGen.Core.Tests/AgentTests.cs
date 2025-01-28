// Copyright (c) Microsoft Corporation. All rights reserved.
// AgentTests.cs
using FluentAssertions;
using Microsoft.AutoGen.Contracts;
using Microsoft.Extensions.Logging;
using Xunit;

namespace Microsoft.AutoGen.Core.Tests;

//[Collection(ClusterFixtureCollection.Name)]
public class AgentTests()
{
    [Fact]
    public async Task Agent_ShouldNotReceiveMessages_WhenNotSubscribed()
    {
        var runtime = new InProcessRuntime();

        Logger<BaseAgent> logger = new(new LoggerFactory());
        await runtime.RegisterAgentFactoryAsync("MyAgent", (id, runtime) => ValueTask.FromResult(new TestAgent(id, runtime, logger)));
        await runtime.RegisterImplicitAgentSubscriptionsAsync<TestAgent>("MyAgent");

        var topicType = "TestTopic";

        await runtime.PublishMessageAsync(new TextMessage { Source = topicType, Content = "test" }, new TopicId("TestTopic")).ConfigureAwait(true);

        //await Task.Yield();
        await Task.Delay(100);

        TestAgent.ReceivedMessages.Any().Should().BeFalse("Agent should not receive messages when not subscribed.");
    }

    [Fact]
    public async Task Agent_ShoulReceiveMessages_WhenSubscribed()
    {
        var runtime = new InProcessRuntime();

        Logger<BaseAgent> logger = new(new LoggerFactory());
        await runtime.RegisterAgentFactoryAsync("MyAgent", (id, runtime) => ValueTask.FromResult(new SubscribedAgent(id, runtime, logger)));
        await runtime.RegisterImplicitAgentSubscriptionsAsync<SubscribedAgent>("MyAgent");

        var topicType = "TestTopic";

        await runtime.PublishMessageAsync(new TextMessage { Source = topicType, Content = "test" }, new TopicId("TestTopic")).ConfigureAwait(true);

        //await Task.Yield();
        await Task.Delay(100);

        TestAgent.ReceivedMessages.Any().Should().BeTrue("Agent should receive messages when subscribed.");
    }

    [Fact]
    public async Task SendMessageAsync_ShouldReturnResponse()
    {
        // Arrange
        var runtime = new InProcessRuntime();
        Logger<BaseAgent> logger = new(new LoggerFactory());
        await runtime.RegisterAgentFactoryAsync("MyAgent", (id, runtime) => ValueTask.FromResult(new TestAgent(id, runtime, logger)));
        await runtime.RegisterImplicitAgentSubscriptionsAsync<TestAgent>("MyAgent");

        var agentId = new AgentId("MyAgent", "TestAgent");
        var response = await runtime.SendMessageAsync(new RpcTextMessage { Source = "TestTopic", Content = "Request" }, agentId);

        // Assert
        Assert.NotNull(response);
        Assert.IsType<string>(response);
        if (response is string responseString)
        {
            Assert.Equal("Request", responseString);
        }
    }

    // / <summary>
    // / Verify that if the agent is not initialized via AgentWorker, it should throw the correct exception.
    // / </summary>
    // / <returns>void</returns>
    // [Fact]
    // public async Task Agent_ShouldThrowException_WhenNotInitialized()
    // {
    //     using var fixture = new InMemoryAgentRuntimeFixture();
    //     var agent = ActivatorUtilities.CreateInstance<TestAgent>(fixture.AppHost.Services);
    //     await Assert.ThrowsAsync<UninitializedAgentWorker.AgentInitalizedIncorrectlyException>(
    //         async () =>
    //         {
    //             await agent.SubscribeAsync("TestEvent");
    //         }
    //     );
    // }

    // /// <summary>
    // /// validate that the agent is initialized correctly with implicit subs
    // /// </summary>
    // /// <returns>void</returns>
    // [Fact]
    // public async Task Agent_ShouldInitializeCorrectly()
    // {
    //     var fixture = new InMemoryAgentRuntimeFixture();
    //     var (runtime, agent) = fixture.Start();
    //     Assert.Equal(nameof(AgentRuntime), runtime.GetType().Name);
    //     var subscriptions = await agent.GetSubscriptionsAsync();
    //     Assert.Equal(2, subscriptions.Count);
    //     fixture.Stop();
    // }
    /// <summary>
    /// Test SubscribeAsync method
    /// </summary>
    /// <returns>void</returns>
    ///

    public class ReceiverAgent(AgentId id,
            IAgentRuntime runtime) : BaseAgent(id, runtime, "Receiver Agent", null),
            IHandle<string>
    {
        public ValueTask HandleAsync(string item, MessageContext messageContext)
        {
            ReceivedItems.Add(item);
            return ValueTask.CompletedTask;
        }

        public List<string> ReceivedItems { get; private set; } = [];
    }

    [Fact]
    public async Task SubscribeAsync_UnsubscribeAsync_and_GetSubscriptionsTest()
    {
        var runtime = new InProcessRuntime();
        ReceiverAgent? agent = null;
        await runtime.RegisterAgentFactoryAsync("MyAgent", (id, runtime) =>
        {
            agent = new ReceiverAgent(id, runtime);
            return ValueTask.FromResult(agent);
        });

        Assert.Null(agent);
        await runtime.GetAgentAsync("MyAgent", lazy: false);
        Assert.NotNull(agent);
        Assert.True(agent.ReceivedItems.Count == 0);

        var topicTypeName = "TestTopic";
        await runtime.PublishMessageAsync("info", new TopicId(topicTypeName));
        await Task.Delay(100);

        Assert.True(agent.ReceivedItems.Count == 0);

        var subscription = new TypeSubscription(topicTypeName, "MyAgent");
        await runtime.AddSubscriptionAsync(subscription);

        await runtime.PublishMessageAsync("info", new TopicId(topicTypeName));
        await Task.Delay(100);
        Assert.True(agent.ReceivedItems.Count == 1);
        Assert.Equal("info", agent.ReceivedItems[0]);

        await runtime.RemoveSubscriptionAsync(subscription.Id);
        await runtime.PublishMessageAsync("info", new TopicId(topicTypeName));
        await Task.Delay(100);
        Assert.True(agent.ReceivedItems.Count == 1);
    }

    // /// <summary>
    // /// Test StoreAsync and ReadAsync methods
    // /// </summary>
    // /// <returns>void</returns>
    // [Fact]
    // public async Task StoreAsync_and_ReadAsyncTest()
    // {
    //     var fixture = new InMemoryAgentRuntimeFixture();
    //     var (_, agent) = fixture.Start();
    //     Dictionary<string, string> state = new()
    //     {
    //         { "testdata", "Active" }
    //     };
    //     await agent.StoreAsync(new AgentState
    //     {
    //         AgentId = agent.AgentId,
    //         TextData = JsonSerializer.Serialize(state)
    //     }).ConfigureAwait(true);
    //     var readState = await agent.ReadAsync<AgentState>(agent.AgentId).ConfigureAwait(true);
    //     var read = JsonSerializer.Deserialize<Dictionary<string, string>>(readState.TextData) ?? new Dictionary<string, string> { { "data", "No state data found" } };
    //     read.TryGetValue("testdata", out var value);
    //     Assert.Equal("Active", value);
    //     fixture.Stop();
    // }

    // /// <summary>
    // /// Test PublishMessageAsync method and ReceiveMessage method
    // /// </summary>
    // /// <returns>void</returns>
    // [Fact]
    // public async Task PublishMessageAsync_and_ReceiveMessageTest()
    // {
    //     var fixture = new InMemoryAgentRuntimeFixture();
    //     var (_, agent) = fixture.Start();
    //     var topicType = "TestTopic";
    //     await agent.SubscribeAsync(topicType).ConfigureAwait(true);
    //     var subscriptions = await agent.GetSubscriptionsAsync().ConfigureAwait(true);
    //     var found = false;
    //     foreach (var subscription in subscriptions)
    //     {
    //         if (subscription.TypeSubscription.TopicType == topicType)
    //         {
    //             found = true;
    //         }
    //     }
    //     Assert.True(found);
    //     await agent.PublishMessageAsync(new TextMessage()
    //     {
    //         Source = topicType,
    //         TextMessage_ = "buffer"
    //     }, topicType).ConfigureAwait(true);
    //     await Task.Delay(100);
    //     Assert.True(TestAgent.ReceivedMessages.ContainsKey(topicType));
    //     fixture.Stop();
    // }

    // [Fact]
    // public async Task InvokeCorrectHandler()
    // {
    //     var agent = new TestAgent(new AgentsMetadata(TypeRegistry.Empty, new Dictionary<string, Type>(), new Dictionary<Type, HashSet<string>>(), new Dictionary<Type, HashSet<string>>()), new Logger<Agent>(new LoggerFactory()));
    //     await agent.HandleObjectAsync("hello world");
    //     await agent.HandleObjectAsync(42);
    //     agent.ReceivedItems.Should().HaveCount(2);
    //     agent.ReceivedItems[0].Should().Be("hello world");
    //     agent.ReceivedItems[1].Should().Be(42);
    // }

    // [Fact]
    // public async Task DelegateMessageToTestAgentAsync()
    // {
    //     var runtime = new InMemoryAgentRuntimeFixture();
    //     var client = runtime.AppHost.Services.GetRequiredService<Client>();
    //     await client.PublishMessageAsync(new TextMessage()
    //     {
    //         Source = nameof(DelegateMessageToTestAgentAsync),
    //         TextMessage_ = "buffer"
    //     }, token: CancellationToken.None);

    //     // wait for 10 seconds
    //     var cts = new CancellationTokenSource(TimeSpan.FromSeconds(10));
    //     while (!TestAgent.ReceivedMessages.ContainsKey(nameof(DelegateMessageToTestAgentAsync)) && !cts.Token.IsCancellationRequested)
    //     {
    //         await Task.Delay(100);
    //     }

    //     TestAgent.ReceivedMessages[nameof(DelegateMessageToTestAgentAsync)].Should().NotBeNull();
    // }

    // [CollectionDefinition(Name)]
    // public sealed class ClusterFixtureCollection : ICollectionFixture<InMemoryAgentRuntimeFixture>
    // {
    //     public const string Name = nameof(ClusterFixtureCollection);
    // }
}
