// Copyright (c) Microsoft Corporation. All rights reserved.
// TestGrpcClient.cs
namespace Microsoft.AutoGen.RuntimeGateway.Grpc.Tests.Helpers.Grpc;
internal sealed class TestGrpcClient<TMessage> : IDisposable
    where TMessage : class
{
    public TestAsyncStreamReader<TMessage> RequestStream { get; }
    public TestServerStreamWriter<TMessage> ResponseStream { get; }
    public TestServerCallContext CallContext { get; }
    private CancellationTokenSource CallContextCancellation = new();
    public TestGrpcClient()
    {
        CallContext = TestServerCallContext.Create(cancellationToken: CallContextCancellation.Token);
        RequestStream = new TestAsyncStreamReader<TMessage>(CallContext);
        ResponseStream = new TestServerStreamWriter<TMessage>(CallContext);
    }

    public async Task<TMessage> ReadNext()
    {
        var response = await ResponseStream.ReadNextAsync();
        return response!;
    }

    public void AddMessage(TMessage message)
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

