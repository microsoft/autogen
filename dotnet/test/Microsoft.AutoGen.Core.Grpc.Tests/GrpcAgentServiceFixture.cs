// Copyright (c) Microsoft Corporation. All rights reserved.
// GrpcAgentServiceFixture.cs
using Grpc.Core;
using Microsoft.AutoGen.Protobuf;
namespace Microsoft.AutoGen.Core.Grpc.Tests;

/// <summary>
/// This fixture is largely just a loopback as we are testing the client side logic of the GrpcAgentRuntime in isolation from the rest of the system.
/// </summary>
public sealed class GrpcAgentServiceFixture() : AgentRpc.AgentRpcBase
{
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
    public override async Task<AddSubscriptionResponse> AddSubscription(AddSubscriptionRequest request, ServerCallContext context) => new AddSubscriptionResponse { };
    public override async Task<RemoveSubscriptionResponse> RemoveSubscription(RemoveSubscriptionRequest request, ServerCallContext context) => new RemoveSubscriptionResponse { };
    public override async Task<GetSubscriptionsResponse> GetSubscriptions(GetSubscriptionsRequest request, ServerCallContext context) => new GetSubscriptionsResponse { };
    public override async Task<RegisterAgentTypeResponse> RegisterAgent(RegisterAgentTypeRequest request, ServerCallContext context) => new RegisterAgentTypeResponse { };
}
