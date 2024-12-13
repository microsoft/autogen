// Copyright (c) Microsoft Corporation. All rights reserved.
// TestGrpcClient.cs

using Microsoft.AutoGen.Contracts;

namespace Microsoft.AutoGen.Runtime.Grpc.Tests.Helpers.Grpc;
internal sealed class TestGrpcClient: IDisposable
{
    public TestAsyncStreamReader<Message> RequestStream { get; }
    public TestServerStreamWriter<Message> ResponseStream { get; }
    public TestServerCallContext CallContext { get; }

    public TestGrpcClient()
    {
        CallContext = TestServerCallContext.Create();
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
        RequestStream.Dispose();
        ResponseStream.Dispose();
    }
}
