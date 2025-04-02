// Copyright (c) Microsoft Corporation. All rights reserved.
// GrpcWorkerConnection.cs
using System.Threading.Channels;
using Grpc.Core;

namespace Microsoft.AutoGen.RuntimeGateway.Grpc;

public sealed class GrpcWorkerConnection<TMessage> : IAsyncDisposable
where TMessage : class
{
    private static long s_nextConnectionId;
    private Task _readTask = Task.CompletedTask;
    private Task _writeTask = Task.CompletedTask;
    private readonly string _connectionId = Interlocked.Increment(ref s_nextConnectionId).ToString();
    private readonly object _lock = new();
    private readonly HashSet<string> _supportedTypes = [];
    private readonly GrpcGateway _gateway;
    private readonly CancellationTokenSource _shutdownCancellationToken = new();
    public Task Completion { get; private set; } = Task.CompletedTask;
    public GrpcWorkerConnection(GrpcGateway agentWorker, IAsyncStreamReader<TMessage> requestStream, IServerStreamWriter<TMessage> responseStream, ServerCallContext context)
    {
        _gateway = agentWorker;
        RequestStream = requestStream;
        ResponseStream = responseStream;
        ServerCallContext = context;
        _outboundMessages = Channel.CreateUnbounded<TMessage>(new UnboundedChannelOptions { AllowSynchronousContinuations = true, SingleReader = true, SingleWriter = false });
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

    public IAsyncStreamReader<TMessage> RequestStream { get; }
    public IServerStreamWriter<TMessage> ResponseStream { get; }
    public ServerCallContext ServerCallContext { get; }

    private readonly Channel<TMessage> _outboundMessages;

    /// <inheritdoc/>
    public void AddSupportedType(string type)
    {
        lock (_lock)
        {
            _supportedTypes.Add(type);
        }
    }

    /// <inheritdoc/>
    public HashSet<string> GetSupportedTypes()
    {
        lock (_lock)
        {
            return new HashSet<string>(_supportedTypes);
        }
    }

    /// <inheritdoc/>
    public async Task SendMessage(TMessage message)
    {
        await _outboundMessages.Writer.WriteAsync(message).ConfigureAwait(false);
    }

    /// <inheritdoc/>
    public async Task RunReadPump()
    {
        await Task.CompletedTask.ConfigureAwait(ConfigureAwaitOptions.ForceYielding);
        try
        {
            await foreach (var message in RequestStream.ReadAllAsync(_shutdownCancellationToken.Token))
            {
                // Fire and forget
                _gateway.OnReceivedMessageAsync(this, message, _shutdownCancellationToken.Token).Ignore();
            }
        }
        catch (OperationCanceledException)
        {
        }
        finally
        {
            _shutdownCancellationToken.Cancel();
            _gateway.OnRemoveWorkerProcess(this);
        }
    }

    /// <inheritdoc/>
    public async Task RunWritePump()
    {
        await Task.CompletedTask.ConfigureAwait(ConfigureAwaitOptions.ForceYielding);
        try
        {
            await foreach (var message in _outboundMessages.Reader.ReadAllAsync(_shutdownCancellationToken.Token).ConfigureAwait(false))
            {
                await ResponseStream.WriteAsync(message).ConfigureAwait(false);
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

    /// <inheritdoc/>
    public async ValueTask DisposeAsync()
    {
        _shutdownCancellationToken.Cancel();
        await Completion.ConfigureAwait(ConfigureAwaitOptions.SuppressThrowing);
    }

    /// <inheritdoc/>
    public override string ToString() => $"Connection-{_connectionId}";
}
