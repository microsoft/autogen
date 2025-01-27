// Copyright (c) Microsoft Corporation. All rights reserved.
// AgentRuntimeTests.cs

using Google.Protobuf;
using Google.Protobuf.Reflection;
using Google.Protobuf.WellKnownTypes;
using Microsoft.AutoGen.Contracts;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;
using Moq;
using Xunit;

namespace Microsoft.AutoGen.Core.Tests;

public class AgentRuntimeTests
{
    private readonly Mock<IHostApplicationLifetime> _hostApplicationLifetimeMock;
    private readonly Mock<IServiceProvider> _serviceProviderMock;
    private readonly Mock<ILogger<AgentRuntime>> _loggerMock;
    private readonly Mock<IRegistry> _registryMock;
    private readonly AgentRuntime _agentRuntime;

    public AgentRuntimeTests()
    {
        _hostApplicationLifetimeMock = new Mock<IHostApplicationLifetime>();
        _serviceProviderMock = new Mock<IServiceProvider>();
        _loggerMock = new Mock<ILogger<AgentRuntime>>();
        _registryMock = new Mock<IRegistry>();

        _serviceProviderMock.Setup(sp => sp.GetService(typeof(IRegistry))).Returns(_registryMock.Object);

        var configuredAgentTypes = new List<Tuple<string, System.Type>>
        {
            new Tuple<string, System.Type>("TestAgent", typeof(TestAgent))
        };

        _agentRuntime = new AgentRuntime(
            _hostApplicationLifetimeMock.Object,
            _serviceProviderMock.Object,
            configuredAgentTypes,
            _loggerMock.Object);
    }

    [Fact]
    public async Task SendMessageAsync_ShouldReturnResponse()
    {
        // Arrange
        var fixture = new InMemoryAgentRuntimeFixture();
        var (runtime, agent) = fixture.Start();
        var agentId = new AgentId { Type = "TestAgent", Key = "test-key" };
        var message = new TextMessage { TextMessage_ = "Hello, World!" };
        var agentMock = new Mock<TestAgent>(MockBehavior.Loose, new AgentsMetadata(TypeRegistry.Empty, new Dictionary<string, System.Type>(), new Dictionary<System.Type, HashSet<string>>(), new Dictionary<System.Type, HashSet<string>>()), new Logger<Agent>(new LoggerFactory()));
        agentMock.CallBase = true; // Enable calling the base class methods
        agentMock.Setup(a => a.HandleObjectAsync(It.IsAny<object>(), It.IsAny<CancellationToken>())).Callback<object, CancellationToken>((msg, ct) =>
        {
            var response = new RpcResponse
            {
                RequestId = "test-request-id",
                Payload = new Payload { Data = Any.Pack(new TextMessage { TextMessage_ = "Response" }).ToByteString() }
            };
            _agentRuntime.DispatchResponse(response);
        });

        // Act
        var response = await runtime.SendMessageAsync(message, agentId, agent.AgentId);

        // Assert
        Assert.NotNull(response);
        var any = Any.Parser.ParseFrom(response.Payload.Data);
        var unpackedMessage = any.Unpack<TextMessage>();
        Assert.Equal("Response", unpackedMessage.TextMessage_);
        fixture.Stop();
    }
}
