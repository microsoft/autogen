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
public class SendMessageTests
{
    private sealed class BasicMessage
    {
        public string Content { get; set; } = string.Empty;
    }

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
                BasicMessage message = new BasicMessage { Content = $"@{targetKey}: item.Content" };
                await this.Runtime.SendMessageAsync(message, targetId);
            }
        }
    }

    private sealed class ReceiverAgent : BaseAgent, IHandle<BasicMessage>
    {
        public List<BasicMessage> Messages { get; } = new();

        public ReceiverAgent(AgentId id, IAgentRuntime runtime, string description, ILogger<BaseAgent>? logger = null)
            : base(id, runtime, description, logger)
        {
        }

        public ValueTask HandleAsync(BasicMessage item, MessageContext messageContext)
        {
            this.Messages.Add(item);

            return ValueTask.CompletedTask;
        }
    }

    private sealed class ProcessorAgent : BaseAgent, IHandle<BasicMessage, BasicMessage>
    {
        private Func<string, string> ProcessFunc { get; }

        public ProcessorAgent(AgentId id, IAgentRuntime runtime, Func<string, string> processFunc, string description, ILogger<BaseAgent>? logger = null)
            : base(id, runtime, description, logger)
        {
            this.ProcessFunc = processFunc;
        }

        public ValueTask<BasicMessage> HandleAsync(BasicMessage item, MessageContext messageContext)
        {
            BasicMessage result = new() { Content = this.ProcessFunc(item.Content) };

            return ValueTask.FromResult(result);
        }
    }

    private sealed class TestException : Exception
    { }

    private sealed class CancelAgent : BaseAgent, IHandle<BasicMessage, BasicMessage>
    {
        public CancelAgent(AgentId id, IAgentRuntime runtime, string description, ILogger<BaseAgent>? logger = null)
            : base(id, runtime, description, logger)
        {
        }

        public ValueTask<BasicMessage> HandleAsync(BasicMessage item, MessageContext messageContext)
        {
            CancellationToken cancelledToken = new CancellationToken(canceled: true);
            cancelledToken.ThrowIfCancellationRequested();

            return ValueTask.FromResult(item);
        }
    }

    private sealed class ErrorAgent : BaseAgent, IHandle<BasicMessage, BasicMessage>
    {
        public ErrorAgent(AgentId id, IAgentRuntime runtime, string description, ILogger<BaseAgent>? logger = null)
            : base(id, runtime, description, logger)
        {
        }

        public ValueTask<BasicMessage> HandleAsync(BasicMessage item, MessageContext messageContext)
        {
            throw new TestException();
        }
    }

    private sealed class SendTestFixture
    {
        private Dictionary<Type, object> AgentsTypeMap { get; } = new();
        public InProcessRuntime Runtime { get; private set; } = new();

        public ValueTask<AgentType> RegisterFactoryMapInstances<TAgent>(AgentType type, Func<AgentId, IAgentRuntime, ValueTask<TAgent>> factory)
            where TAgent : IHostableAgent
        {
            Func<AgentId, IAgentRuntime, ValueTask<TAgent>> wrappedFactory = async (id, runtime) =>
            {
                TAgent agent = await factory(id, runtime);
                this.GetAgentInstances<TAgent>()[id] = agent;
                return agent;
            };

            return this.Runtime.RegisterAgentFactoryAsync(type, wrappedFactory);
        }

        public Dictionary<AgentId, TAgent> GetAgentInstances<TAgent>() where TAgent : IHostableAgent
        {
            if (!AgentsTypeMap.TryGetValue(typeof(TAgent), out object? maybeAgentMap) ||
                maybeAgentMap is not Dictionary<AgentId, TAgent> result)
            {
                this.AgentsTypeMap[typeof(TAgent)] = result = new Dictionary<AgentId, TAgent>();
            }

            return result;
        }

        public async ValueTask<object?> RunTestAsync(AgentId sendTarget, object message, string? messageId = null)
        {
            messageId ??= Guid.NewGuid().ToString();

            await this.Runtime.StartAsync();

            object? result = await this.Runtime.SendMessageAsync(message, sendTarget, messageId: messageId);

            await this.Runtime.RunUntilIdleAsync();

            return result;
        }
    }

    [Fact]
    public async Task Test_SendMessage_ReturnsValue()
    {
        Func<string, string> ProcessFunc = (s) => $"Processed({s})";

        SendTestFixture fixture = new SendTestFixture();

        await fixture.RegisterFactoryMapInstances(nameof(ProcessorAgent),
            (id, runtime) => ValueTask.FromResult(new ProcessorAgent(id, runtime, ProcessFunc, string.Empty)));

        AgentId targetAgent = new AgentId(nameof(ProcessorAgent), Guid.NewGuid().ToString());
        object? maybeResult = await fixture.RunTestAsync(targetAgent, new BasicMessage { Content = "1" });

        maybeResult.Should().NotBeNull()
                        .And.BeOfType<BasicMessage>()
                        .And.Match<BasicMessage>(m => m.Content == "Processed(1)");
    }

    [Fact]
    public async Task Test_SendMessage_Cancellation()
    {
        SendTestFixture fixture = new SendTestFixture();

        await fixture.RegisterFactoryMapInstances(nameof(CancelAgent),
            (id, runtime) => ValueTask.FromResult(new CancelAgent(id, runtime, string.Empty)));

        AgentId targetAgent = new AgentId(nameof(CancelAgent), Guid.NewGuid().ToString());
        Func<Task> testAction = () => fixture.RunTestAsync(targetAgent, new BasicMessage { Content = "1" }).AsTask();

        // TODO: Do we want to do the unwrap in this case?
        await testAction.Should().ThrowAsync<OperationCanceledException>();
    }

    [Fact]
    public async Task Test_SendMessage_Error()
    {
        SendTestFixture fixture = new SendTestFixture();

        await fixture.RegisterFactoryMapInstances(nameof(ErrorAgent),
            (id, runtime) => ValueTask.FromResult(new ErrorAgent(id, runtime, string.Empty)));

        AgentId targetAgent = new AgentId(nameof(ErrorAgent), Guid.NewGuid().ToString());
        Func<Task> testAction = () => fixture.RunTestAsync(targetAgent, new BasicMessage { Content = "1" }).AsTask();

        (await testAction.Should().ThrowAsync<TargetInvocationException>())
                                  .WithInnerException<TestException>();
    }

    [Fact]
    public async Task TesT_SendMessage_FromSendMessageHandler()
    {
        Guid[] targetGuids = [Guid.NewGuid(), Guid.NewGuid()];

        SendTestFixture fixture = new SendTestFixture();

        Dictionary<AgentId, SendOnAgent> sendAgents = fixture.GetAgentInstances<SendOnAgent>();
        Dictionary<AgentId, ReceiverAgent> receiverAgents = fixture.GetAgentInstances<ReceiverAgent>();

        await fixture.RegisterFactoryMapInstances(nameof(SendOnAgent),
            (id, runtime) => ValueTask.FromResult(new SendOnAgent(id, runtime, string.Empty, targetGuids)));

        await fixture.RegisterFactoryMapInstances(nameof(ReceiverAgent),
            (id, runtime) => ValueTask.FromResult(new ReceiverAgent(id, runtime, string.Empty)));

        AgentId targetAgent = new AgentId(nameof(SendOnAgent), Guid.NewGuid().ToString());
        Task testTask = fixture.RunTestAsync(targetAgent, new BasicMessage { Content = "Hello" }).AsTask();

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
            receiverAgents[targetId].Messages.Should().ContainSingle(m => m.Content == $"@{targetKey}: item.Content");
        }
    }
}
