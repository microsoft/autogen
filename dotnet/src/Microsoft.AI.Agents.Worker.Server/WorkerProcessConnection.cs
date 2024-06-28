using Grpc.Core;
using Agents;

namespace Microsoft.AI.Agents.Worker;

internal sealed class WorkerProcessConnection : IAsyncDisposable
{
    private static long s_nextConnectionId;
    private readonly string _connectionId = Interlocked.Increment(ref s_nextConnectionId).ToString();
    private readonly object _lock = new();
    private readonly HashSet<string> _supportedTypes = [];
    private readonly WorkerGateway _gateway;
    private readonly CancellationTokenSource _shutdownCancellationToken = new();

    public WorkerProcessConnection(WorkerGateway agentWorker, IAsyncStreamReader<Message> requestStream, IServerStreamWriter<Message> responseStream, ServerCallContext context)
    {
        _gateway = agentWorker;
        RequestStream = requestStream;
        ResponseStream = responseStream;
        ServerCallContext = context;
        Completion = Start();
    }

    public IAsyncStreamReader<Message> RequestStream { get; }
    public IServerStreamWriter<Message> ResponseStream { get; }
    public ServerCallContext ServerCallContext { get; }

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
        await ResponseStream.WriteAsync(message);
    }

    public Task Completion { get; }

    private Task Start()
    {
        var didSuppress = false;
        if (!ExecutionContext.IsFlowSuppressed())
        {
            didSuppress = true;
            ExecutionContext.SuppressFlow();
        }

        try
        {
            return Task.Run(Run);
        }
        finally
        {
            if (didSuppress)
            {
                ExecutionContext.RestoreFlow();
            }
        }
    }

    public async Task Run()
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
        finally
        {
            _gateway.OnRemoveWorkerProcess(this);
        }
    }

    public async ValueTask DisposeAsync()
    {
        _shutdownCancellationToken.Cancel();
        await Completion.ConfigureAwait(ConfigureAwaitOptions.SuppressThrowing);
    }

    public override string ToString() => $"Connection-{_connectionId}";
}
