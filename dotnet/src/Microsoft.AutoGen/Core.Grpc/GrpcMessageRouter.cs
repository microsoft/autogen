// Copyright (c) Microsoft Corporation. All rights reserved.
// GrpcMessageRouter.cs

using System.Threading.Channels;
using Grpc.Core;
using Microsoft.AutoGen.Protobuf;
using Microsoft.Extensions.Logging;

namespace Microsoft.AutoGen.Core.Grpc;

// TODO: Consider whether we want to just reuse IHandle
internal interface IMessageSink<TMessage>
{
    public ValueTask OnMessageAsync(TMessage message, CancellationToken cancellation = default);
}

internal sealed class AutoRestartChannel : IDisposable
{
    private readonly object _channelLock = new();
    private readonly AgentRpc.AgentRpcClient _client;
    private readonly Guid _clientId;
    private readonly ILogger<GrpcAgentRuntime> _logger;
    private readonly CancellationTokenSource _shutdownCts;
    private AsyncDuplexStreamingCall<Message, Message>? _channel;

    public AutoRestartChannel(AgentRpc.AgentRpcClient client,
                              Guid clientId,
                              ILogger<GrpcAgentRuntime> logger,
                              CancellationToken shutdownCancellation = default)
    {
        _client = client;
        _clientId = clientId;
        _logger = logger;
        _shutdownCts = CancellationTokenSource.CreateLinkedTokenSource(shutdownCancellation);
    }

    public bool Connected { get => _channel is not null; }

    public void EnsureConnected()
    {
        _logger.LogInformation("Connecting to gRPC endpoint " + Environment.GetEnvironmentVariable("AGENT_HOST"));

        if (this.RecreateChannel(null) == null)
        {
            throw new Exception("Failed to connect to gRPC endpoint.");
        };
    }

    public AsyncDuplexStreamingCall<Message, Message> StreamingCall
    {
        get
        {
            if (_channel is { } channel)
            {
                return channel;
            }

            lock (_channelLock)
            {
                if (_channel is not null)
                {
                    return _channel;
                }

                return RecreateChannel(null);
            }
        }
    }

    public AsyncDuplexStreamingCall<Message, Message> RecreateChannel() => RecreateChannel(this._channel);

    private AsyncDuplexStreamingCall<Message, Message> RecreateChannel(AsyncDuplexStreamingCall<Message, Message>? ownedChannel)
    {
        // Make sure we are only re-creating the channel if it does not exit or we are the owner.
        if (_channel is null || _channel == ownedChannel)
        {
            lock (_channelLock)
            {
                if (_channel is null || _channel == ownedChannel)
                {
                    var metadata = new Metadata
                    {
                        { "client-id", _clientId.ToString() }
                    };
                    _channel?.Dispose();
                    _channel = _client.OpenChannel(cancellationToken: _shutdownCts.Token, headers: metadata);
                }
            }
        }

        return _channel;
    }

    public void Dispose()
    {
        IDisposable? channelDisposable = Interlocked.Exchange(ref this._channel, null);
        channelDisposable?.Dispose();
    }
}

internal sealed class GrpcMessageRouter(AgentRpc.AgentRpcClient client,
                                    IMessageSink<Message> incomingMessageSink,
                                    Guid clientId,
                                    ILogger<GrpcAgentRuntime> logger,
                                    CancellationToken shutdownCancellation = default) : IDisposable
{
    private static readonly BoundedChannelOptions DefaultChannelOptions = new BoundedChannelOptions(1024)
    {
        AllowSynchronousContinuations = true,
        SingleReader = true,
        SingleWriter = false,
        FullMode = BoundedChannelFullMode.Wait
    };

    private readonly ILogger<GrpcAgentRuntime> _logger = logger;

    private readonly CancellationTokenSource _shutdownCts = CancellationTokenSource.CreateLinkedTokenSource(shutdownCancellation);

    private readonly IMessageSink<Message> _incomingMessageSink = incomingMessageSink;
    private readonly Channel<(Message Message, TaskCompletionSource WriteCompletionSource)> _outboundMessagesChannel
        // TODO: Enable a way to configure the channel options
        = Channel.CreateBounded<(Message, TaskCompletionSource)>(DefaultChannelOptions);

    private readonly AutoRestartChannel _incomingMessageChannel = new AutoRestartChannel(client, clientId, logger, shutdownCancellation);

    private Task? _readTask;
    private Task? _writeTask;

    private async Task RunReadPump()
    {
        var cachedChannel = _incomingMessageChannel.StreamingCall;
        while (!_shutdownCts.Token.IsCancellationRequested)
        {
            try
            {
                await foreach (var message in cachedChannel.ResponseStream.ReadAllAsync(_shutdownCts.Token))
                {
                    // next if message is null
                    if (message == null)
                    {
                        continue;
                    }

                    await _incomingMessageSink.OnMessageAsync(message, _shutdownCts.Token);
                }
            }
            catch (OperationCanceledException)
            {
                // Time to shut down.
                break;
            }
            catch (Exception ex) when (!_shutdownCts.IsCancellationRequested)
            {
                _logger.LogError(ex, "Error reading from channel.");
                cachedChannel = this._incomingMessageChannel.RecreateChannel();
            }
            catch
            {
                // Shutdown requested.
                break;
            }
        }
    }

    private async Task RunWritePump()
    {
        var cachedChannel = this._incomingMessageChannel.StreamingCall;
        var outboundMessages = _outboundMessagesChannel.Reader;
        while (!_shutdownCts.IsCancellationRequested)
        {
            (Message Message, TaskCompletionSource WriteCompletionSource) item = default;
            try
            {
                await outboundMessages.WaitToReadAsync().ConfigureAwait(false);

                // Read the next message if we don't already have an unsent message
                // waiting to be sent.
                if (!outboundMessages.TryRead(out item))
                {
                    break;
                }

                while (!_shutdownCts.IsCancellationRequested)
                {
                    await cachedChannel.RequestStream.WriteAsync(item.Message, _shutdownCts.Token).ConfigureAwait(false);
                    item.WriteCompletionSource.TrySetResult();
                    break;
                }
            }
            catch (OperationCanceledException)
            {
                // Time to shut down.
                item.WriteCompletionSource?.TrySetCanceled();
                break;
            }
            catch (RpcException ex) when (ex.StatusCode == StatusCode.Unavailable)
            {
                // we could not connect to the endpoint - most likely we have the wrong port or failed ssl
                // we need to let the user know what port we tried to connect to and then do backoff and retry
                _logger.LogError(ex, "Error connecting to GRPC endpoint {Endpoint}.", Environment.GetEnvironmentVariable("AGENT_HOST"));
                break;
            }
            catch (RpcException ex) when (ex.StatusCode == StatusCode.OK)
            {
                _logger.LogError(ex, "Error writing to channel, continuing (Status OK). {ex}", cachedChannel.ToString());
                break;
            }
            catch (Exception ex) when (!_shutdownCts.IsCancellationRequested)
            {
                item.WriteCompletionSource?.TrySetException(ex);
                _logger.LogError(ex, $"Error writing to channel.{ex}");
                cachedChannel = this._incomingMessageChannel.RecreateChannel();
                continue;
            }
            catch
            {
                // Shutdown requested.
                item.WriteCompletionSource?.TrySetCanceled();
                break;
            }
        }

        while (outboundMessages.TryRead(out var item))
        {
            item.WriteCompletionSource.TrySetCanceled();
        }
    }

    public ValueTask RouteMessageAsync(Message message, CancellationToken cancellation = default)
    {
        var tcs = new TaskCompletionSource();
        return _outboundMessagesChannel.Writer.WriteAsync((message, tcs), cancellation);
    }

    public ValueTask StartAsync(CancellationToken cancellation)
    {
        // TODO: Should we error out on a noncancellable token?

        this._incomingMessageChannel.EnsureConnected();
        var didSuppress = false;

        // Make sure we do not mistakenly flow the ExecutionContext into the background pumping tasks.
        if (!ExecutionContext.IsFlowSuppressed())
        {
            didSuppress = true;
            ExecutionContext.SuppressFlow();
        }

        try
        {
            _readTask = Task.Run(RunReadPump, cancellation);
            _writeTask = Task.Run(RunWritePump, cancellation);

            return ValueTask.CompletedTask;
        }
        catch (Exception ex)
        {
            return ValueTask.FromException(ex);
        }
        finally
        {
            if (didSuppress)
            {
                ExecutionContext.RestoreFlow();
            }
        }
    }

    // No point in returning a ValueTask here, since we are awaiting the two tasks
    public async Task StopAsync()
    {
        _shutdownCts.Cancel();

        _outboundMessagesChannel.Writer.TryComplete();

        List<Task> pendingTasks = new();
        if (_readTask is { } readTask)
        {
            pendingTasks.Add(readTask);
        }

        if (_writeTask is { } writeTask)
        {
            pendingTasks.Add(writeTask);
        }

        await Task.WhenAll(pendingTasks).ConfigureAwait(false);

        this._incomingMessageChannel.Dispose();
    }

    public bool IsChannelOpen => this._incomingMessageChannel.Connected;

    public void Dispose()
    {
        _outboundMessagesChannel.Writer.TryComplete();
        this._incomingMessageChannel.Dispose();
    }
}

