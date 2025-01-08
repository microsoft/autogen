// Copyright (c) Microsoft Corporation. All rights reserved.
// GrpcWorkerConnection.cs

using System.Threading.Channels;
using Grpc.Core;
using Microsoft.AutoGen.Contracts;

namespace Microsoft.AutoGen.Runtime.Grpc;

internal sealed class GrpcWorkerConnection : IAsyncDisposable
{
    private static long s_nextConnectionId;
    private Task? _readTask;
    private Task? _writeTask;
    private readonly string _connectionId = Interlocked.Increment(ref s_nextConnectionId).ToString();
    private readonly object _lock = new();
    private readonly HashSet<string> _supportedTypes = [];
    private readonly GrpcGateway _gateway;
    private readonly CancellationTokenSource _shutdownCancellationToken = new();
    public Task? Completion { get; private set; }

    public GrpcWorkerConnection(GrpcGateway agentWorker, IAsyncStreamReader<Message> requestStream, IServerStreamWriter<Message> responseStream, ServerCallContext context)
    {
        _gateway = agentWorker;
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
        Completion = Task.WhenAll(_readTask, _writeTask);

        return Completion;
    }

    public IAsyncStreamReader<Message> RequestStream { get; }
    public IServerStreamWriter<Message> ResponseStream { get; }
    public ServerCallContext ServerCallContext { get; }

    private readonly Channel<Message> _outboundMessages;

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

                // Fire and forget
                _gateway.OnReceivedMessageAsync(this, message).Ignore();
            }
        }
        catch (OperationCanceledException)
        {
        }
        finally
        {
            await _shutdownCancellationToken.CancelAsync();
            _gateway.OnRemoveWorkerProcess(this);
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
        if (Completion is not null)
        {
            await Completion.ConfigureAwait(ConfigureAwaitOptions.SuppressThrowing);
        }
    }

    public override string ToString() => $"Connection-{_connectionId}";
}
