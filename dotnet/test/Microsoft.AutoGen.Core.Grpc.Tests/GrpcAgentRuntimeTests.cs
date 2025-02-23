// Copyright (c) Microsoft Corporation. All rights reserved.
// GrpcAgentRuntimeTests.cs

using FluentAssertions;
using Microsoft.AutoGen.Contracts;
using Microsoft.Extensions.Logging;
using Xunit;

namespace Microsoft.AutoGen.Core.Grpc.Tests;

[Trait("Category", "GRPC")]
public class GrpcAgentRuntimeTests : TestBase
{
    [Fact]
    public async Task GatewayShouldNotReceiveRegistrationsUntilRuntimeStart()
    {
        var fixture = new GrpcAgentRuntimeFixture();
        var runtime = (GrpcAgentRuntime)await fixture.StartAsync(startRuntime: false, registerDefaultAgent: false);

        Logger<BaseAgent> logger = new(new LoggerFactory());

        await runtime.RegisterAgentFactoryAsync("MyAgent", async (id, runtime) =>
        {
            return await ValueTask.FromResult(new SubscribedProtobufAgent(id, runtime, logger));
        });
        await runtime.RegisterImplicitAgentSubscriptionsAsync<SubscribedProtobufAgent>("MyAgent");

        fixture.GrpcRequestCollector.RegisterAgentTypeRequests.Should().BeEmpty();
        fixture.GrpcRequestCollector.AddSubscriptionRequests.Should().BeEmpty();

        await fixture.AgentsApp!.StartAsync().ConfigureAwait(true);

        fixture.GrpcRequestCollector.RegisterAgentTypeRequests.Should().NotBeEmpty();
        fixture.GrpcRequestCollector.RegisterAgentTypeRequests.Single().Type.Should().Be("MyAgent");
        fixture.GrpcRequestCollector.AddSubscriptionRequests.Should().NotBeEmpty();

        fixture.GrpcRequestCollector.Clear();

        await runtime.RegisterAgentFactoryAsync("MyAgent2", async (id, runtime) =>
        {
            return await ValueTask.FromResult(new TestProtobufAgent(id, runtime, logger));
        });

        fixture.GrpcRequestCollector.RegisterAgentTypeRequests.Should().NotBeEmpty();
        fixture.GrpcRequestCollector.RegisterAgentTypeRequests.Single().Type.Should().Be("MyAgent2");
        fixture.GrpcRequestCollector.AddSubscriptionRequests.Should().BeEmpty();

        fixture.Dispose();
    }
}
