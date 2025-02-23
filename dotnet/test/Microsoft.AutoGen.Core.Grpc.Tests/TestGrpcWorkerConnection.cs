// Copyright (c) Microsoft Corporation. All rights reserved.
// TestGrpcWorkerConnection.cs

using System.Threading.Channels;
using Grpc.Core;
using Microsoft.AutoGen.Protobuf;

namespace Microsoft.AutoGen.Core.Grpc.Tests;

internal sealed class TestGrpcWorkerConnection : IAsyncDisposable
{
    private static long s_nextConnectionId;
    private Task _readTask = Task.CompletedTask;
    private Task _writeTask = Task.CompletedTask;
    private readonly string _connectionId = Interlocked.Increment(ref s_nextConnectionId).ToString();
    private readonly object _lock = new();
    private readonly HashSet<string> _supportedTypes = [];
    private readonly CancellationTokenSource _shutdownCancellationToken = new();
    public Task Completion { get; private set; } = Task.CompletedTask;
    public IAsyncStreamReader<Message> RequestStream { get; }
    public IServerStreamWriter<Message> ResponseStream { get; }
    public ServerCallContext ServerCallContext { get; }
    private readonly Channel<Message> _outboundMessages;
    public TestGrpcWorkerConnection(IAsyncStreamReader<Message> requestStream, IServerStreamWriter<Message> responseStream, ServerCallContext context)
    {
        RequestStream = requestStream;
        ResponseStream = responseStream;
        ServerCallContext = context;
        _outboundMessages = Channel.CreateUnbounded<Message>(new UnboundedChannelOptions { AllowSynchronousContinuations = true, SingleReader = true, SingleWriter = false });
    }
    public Task Connect()
    {
        var didSuppress = false;
        if (!ExecutionContext.IsFlowSuppressed())
        {
            didSuppress = true;
            ExecutionContext.SuppressFlow();
        }

        try
        {
            _readTask = Task.Run(RunReadPump);
            _writeTask = Task.Run(RunWritePump);
        }
        finally
        {
            if (didSuppress)
            {
                ExecutionContext.RestoreFlow();
            }
        }

        return Completion = Task.WhenAll(_readTask, _writeTask);
    }
    public void AddSupportedType(string type)
    {
        lock (_lock)
        {
            _supportedTypes.Add(type);
        }
    }
    public HashSet<string> GetSupportedTypes()
    {
        lock (_lock)
        {
            return new HashSet<string>(_supportedTypes);
        }
    }
    public async Task SendMessage(Message message)
    {
        await _outboundMessages.Writer.WriteAsync(message).ConfigureAwait(false);
    }
    public async Task RunReadPump()
    {
        await Task.CompletedTask.ConfigureAwait(ConfigureAwaitOptions.ForceYielding);
        try
        {
            await foreach (var message in RequestStream.ReadAllAsync(_shutdownCancellationToken.Token))
            {
                //_gateway.OnReceivedMessageAsync(this, message, _shutdownCancellationToken.Token).Ignore();
                switch (message.MessageCase)
                {
                    case Message.MessageOneofCase.Request:
                        await SendMessage(new Message { Request = message.Request }).ConfigureAwait(false);
                        break;
                    case Message.MessageOneofCase.Response:
                        await SendMessage(new Message { Response = message.Response }).ConfigureAwait(false);
                        break;
                    case Message.MessageOneofCase.CloudEvent:
                        await SendMessage(new Message { CloudEvent = message.CloudEvent }).ConfigureAwait(false);
                        break;
                    default:
                        // if it wasn't recognized return bad request
                        throw new RpcException(new Status(StatusCode.InvalidArgument, $"Unknown message type for message '{message}'"));
                }
            }
        }
        catch (OperationCanceledException)
        {
        }
        finally
        {
            _shutdownCancellationToken.Cancel();
            //_gateway.OnRemoveWorkerProcess(this);
        }
    }

    public async Task RunWritePump()
    {
        await Task.CompletedTask.ConfigureAwait(ConfigureAwaitOptions.ForceYielding);
        try
        {
            await foreach (var message in _outboundMessages.Reader.ReadAllAsync(_shutdownCancellationToken.Token))
            {
                await ResponseStream.WriteAsync(message);
            }
        }
        catch (OperationCanceledException)
        {
        }
        finally
        {
            _shutdownCancellationToken.Cancel();
        }
    }

    public async ValueTask DisposeAsync()
    {
        _shutdownCancellationToken.Cancel();
        await Completion.ConfigureAwait(ConfigureAwaitOptions.SuppressThrowing);
    }

    public override string ToString() => $"Connection-{_connectionId}";
}
