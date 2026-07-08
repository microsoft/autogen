// Copyright (c) Microsoft Corporation. All rights reserved.
// SendMessageTests.cs

using System.Diagnostics;
using System.Reflection;
using FluentAssertions;
using Microsoft.AutoGen.Contracts;
using Microsoft.Extensions.Logging;
using Xunit;

namespace Microsoft.AutoGen.Core.Tests;

[Trait("Category", "UnitV2")]
public partial class SendMessageTests
{
    private sealed class SendOnAgent : BaseAgent, IHandle<BasicMessage>
    {
        private IList<Guid> targetKeys;

        public SendOnAgent(AgentId id, IAgentRuntime runtime, string description, IList<Guid> targetKeys, ILogger<BaseAgent>? logger = null)
            : base(id, runtime, description, logger)
        {
            this.targetKeys = targetKeys;
        }

        public async ValueTask HandleAsync(BasicMessage item, MessageContext messageContext)
        {
            foreach (Guid targetKey in targetKeys)
            {
                AgentId targetId = new(nameof(ReceiverAgent), targetKey.ToString());
                BasicMessage message = new BasicMessage { Content = $"@{targetKey}: {item.Content}" };
                await this.Runtime.SendMessageAsync(message, targetId);
            }
        }
    }

    [Fact]
    public async Task Test_SendMessage_ReturnsValue()
    {
        Func<string, string> ProcessFunc = (s) => $"Processed({s})";

        MessagingTestFixture fixture = new MessagingTestFixture();

        await fixture.RegisterFactoryMapInstances(nameof(ProcessorAgent),
            (id, runtime) => ValueTask.FromResult(new ProcessorAgent(id, runtime, ProcessFunc, string.Empty)));

        AgentId targetAgent = new AgentId(nameof(ProcessorAgent), Guid.NewGuid().ToString());
        object? maybeResult = await fixture.RunSendTestAsync(targetAgent, new BasicMessage { Content = "1" });

        maybeResult.Should().NotBeNull()
                        .And.BeOfType<BasicMessage>()
                        .And.Match<BasicMessage>(m => m.Content == "Processed(1)");
    }

    [Fact]
    public async Task Test_SendMessage_Cancellation()
    {
        MessagingTestFixture fixture = new MessagingTestFixture();

        await fixture.RegisterFactoryMapInstances(nameof(CancelAgent),
            (id, runtime) => ValueTask.FromResult(new CancelAgent(id, runtime, string.Empty)));

        AgentId targetAgent = new AgentId(nameof(CancelAgent), Guid.NewGuid().ToString());
        Func<Task> testAction = () => fixture.RunSendTestAsync(targetAgent, new BasicMessage { Content = "1" }).AsTask();

        // TODO: Do we want to do the unwrap in this case?
        await testAction.Should().ThrowAsync<OperationCanceledException>();
    }

    [Fact]
    public async Task Test_SendMessage_Error()
    {
        MessagingTestFixture fixture = new MessagingTestFixture();

        await fixture.RegisterFactoryMapInstances(nameof(ErrorAgent),
            (id, runtime) => ValueTask.FromResult(new ErrorAgent(id, runtime, string.Empty)));

        AgentId targetAgent = new AgentId(nameof(ErrorAgent), Guid.NewGuid().ToString());
        Func<Task> testAction = () => fixture.RunSendTestAsync(targetAgent, new BasicMessage { Content = "1" }).AsTask();

        (await testAction.Should().ThrowAsync<TargetInvocationException>())
                                  .WithInnerException<TestException>();
    }

    [Fact]
    public async Task TesT_SendMessage_FromSendMessageHandler()
    {
        Guid[] targetGuids = [Guid.NewGuid(), Guid.NewGuid()];

        MessagingTestFixture fixture = new MessagingTestFixture();

        Dictionary<AgentId, SendOnAgent> sendAgents = fixture.GetAgentInstances<SendOnAgent>();
        Dictionary<AgentId, ReceiverAgent> receiverAgents = fixture.GetAgentInstances<ReceiverAgent>();

        await fixture.RegisterFactoryMapInstances(nameof(SendOnAgent),
            (id, runtime) => ValueTask.FromResult(new SendOnAgent(id, runtime, string.Empty, targetGuids)));

        await fixture.RegisterFactoryMapInstances(nameof(ReceiverAgent),
            (id, runtime) => ValueTask.FromResult(new ReceiverAgent(id, runtime, string.Empty)));

        const string HelloContent = "Hello";
        AgentId targetAgent = new AgentId(nameof(SendOnAgent), Guid.NewGuid().ToString());
        Task testTask = fixture.RunSendTestAsync(targetAgent, new BasicMessage { Content = HelloContent }).AsTask();

        // We do not actually expect to wait the timeout here, but it is still better than waiting the 10 min
        // timeout that the tests default to. A failure will fail regardless of what timeout value we set.
        TimeSpan timeout = Debugger.IsAttached ? TimeSpan.FromSeconds(120) : TimeSpan.FromSeconds(10);
        Task timeoutTask = Task.Delay(timeout);

        Task completedTask = await Task.WhenAny([testTask, timeoutTask]);
        completedTask.Should().Be(testTask, "SendOnAgent should complete before timeout");

        // Check that each of the target agents received the message
        foreach (var targetKey in targetGuids)
        {
            var targetId = new AgentId(nameof(ReceiverAgent), targetKey.ToString());
            receiverAgents[targetId].Messages.Should().ContainSingle(m => m.Content == $"@{targetKey}: {HelloContent}");
        }
    }
}
