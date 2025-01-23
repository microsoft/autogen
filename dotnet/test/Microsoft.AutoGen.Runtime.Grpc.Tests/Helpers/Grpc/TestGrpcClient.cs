// Copyright (c) Microsoft Corporation. All rights reserved.
// TestGrpcClient.cs

using Microsoft.AutoGen.Contracts;

namespace Microsoft.AutoGen.Runtime.Grpc.Tests.Helpers.Grpc;
internal sealed class TestGrpcClient : IDisposable
{
    public TestAsyncStreamReader<Message> RequestStream { get; }
    public TestServerStreamWriter<Message> ResponseStream { get; }
    public TestServerCallContext CallContext { get; }

    private CancellationTokenSource CallContextCancellation = new();
    public TestGrpcClient()
    {
        CallContext = TestServerCallContext.Create(cancellationToken: CallContextCancellation.Token);
        RequestStream = new TestAsyncStreamReader<Message>(CallContext);
        ResponseStream = new TestServerStreamWriter<Message>(CallContext);
    }

    public async Task<Message> ReadNext()
    {
        var response = await ResponseStream.ReadNextAsync();
        return response!;
    }

    public void AddMessage(Message message)
    {
        RequestStream.AddMessage(message);
    }

    public void Dispose()
    {
        CallContextCancellation.Cancel();
        RequestStream.Dispose();
        ResponseStream.Dispose();
    }
}
