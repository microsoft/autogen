// Copyright (c) Microsoft Corporation. All rights reserved.
// GrpcAgentServiceFixture.cs

using Grpc.Core;
using Microsoft.AutoGen.Protobuf;
using Microsoft.Extensions.DependencyInjection;

namespace Microsoft.AutoGen.Core.Grpc.Tests;

public sealed class GrpcAgentServiceCollector
{
    public List<AddSubscriptionRequest> AddSubscriptionRequests { get; } = new();
    public List<RemoveSubscriptionRequest> RemoveSubscriptionRequests { get; } = new();
    public List<RegisterAgentTypeRequest> RegisterAgentTypeRequests { get; } = new();

    internal void Clear()
    {
        this.AddSubscriptionRequests.Clear();
        this.RemoveSubscriptionRequests.Clear();
        this.RegisterAgentTypeRequests.Clear();
    }
}

/// <summary>
/// This fixture is largely just a loopback as we are testing the client side logic of the GrpcAgentRuntime in isolation from the rest of the system.
/// </summary>
public class GrpcAgentServiceFixture : AgentRpc.AgentRpcBase
{
    private GrpcAgentServiceCollector requestCollector;
    public GrpcAgentServiceFixture(IServiceProvider serviceProvider)
    {
        this.requestCollector = serviceProvider.GetService<GrpcAgentServiceCollector>() ?? new();
    }

    public override async Task OpenChannel(IAsyncStreamReader<Message> requestStream, IServerStreamWriter<Message> responseStream, ServerCallContext context)
    {
        try
        {
            var workerProcess = new TestGrpcWorkerConnection(requestStream, responseStream, context);
            await workerProcess.Connect().ConfigureAwait(true);
        }
        catch
        {
            if (context.CancellationToken.IsCancellationRequested)
            {
                return;
            }
            throw;
        }
    }

    public List<AddSubscriptionRequest> AddSubscriptionRequests => this.requestCollector.AddSubscriptionRequests;
    public override async Task<AddSubscriptionResponse> AddSubscription(AddSubscriptionRequest request, ServerCallContext context)
    {
        this.AddSubscriptionRequests.Add(request);
        return new AddSubscriptionResponse();
    }

    public List<RemoveSubscriptionRequest> RemoveSubscriptionRequests => this.requestCollector.RemoveSubscriptionRequests;
    public override async Task<RemoveSubscriptionResponse> RemoveSubscription(RemoveSubscriptionRequest request, ServerCallContext context)
    {
        this.RemoveSubscriptionRequests.Add(request);
        return new RemoveSubscriptionResponse();
    }

    public override async Task<GetSubscriptionsResponse> GetSubscriptions(GetSubscriptionsRequest request, ServerCallContext context) => new GetSubscriptionsResponse { };

    public List<RegisterAgentTypeRequest> RegisterAgentTypeRequests => this.requestCollector.RegisterAgentTypeRequests;
    public override async Task<RegisterAgentTypeResponse> RegisterAgent(RegisterAgentTypeRequest request, ServerCallContext context)
    {
        this.RegisterAgentTypeRequests.Add(request);
        return new RegisterAgentTypeResponse();
    }
}
