// Copyright (c) Microsoft Corporation. All rights reserved.
// Utils.cs

using System.Collections;
using System.Collections.Immutable;
using Microsoft.DotNet.Interactive;
using Microsoft.DotNet.Interactive.Commands;
using Microsoft.DotNet.Interactive.Connection;
using Microsoft.DotNet.Interactive.Events;

public static class ObservableExtensions
{
    public static SubscribedList<T> ToSubscribedList<T>(this IObservable<T> source)
    {
        return new SubscribedList<T>(source);
    }
}

public static class KernelExtensions
{
    internal static void SetUpValueSharingIfSupported(this ProxyKernel proxyKernel)
    {
        var supportedCommands = proxyKernel.KernelInfo.SupportedKernelCommands;
        if (supportedCommands.Any(d => d.Name == nameof(RequestValue)) &&
            supportedCommands.Any(d => d.Name == nameof(SendValue)))
        {
            proxyKernel.UseValueSharing();
        }
    }

    internal static async Task<KernelCommandResult> SendAndThrowOnCommandFailedAsync(
        this Kernel kernel,
        KernelCommand command,
        CancellationToken cancellationToken)
    {
        var result = await kernel.SendAsync(command, cancellationToken);
        result.ThrowOnCommandFailed();
        return result;
    }

    private static void ThrowOnCommandFailed(this KernelCommandResult result)
    {
        var failedEvents = result.Events.OfType<CommandFailed>();
        if (!failedEvents.Any())
        {
            return;
        }

        if (failedEvents.Skip(1).Any())
        {
            var innerExceptions = failedEvents.Select(f => f.GetException());
            throw new AggregateException(innerExceptions);
        }
        else
        {
            throw failedEvents.Single().GetException();
        }
    }

    private static Exception GetException(this CommandFailed commandFailedEvent)
        => new Exception(commandFailedEvent.Message);
}

public class SubscribedList<T> : IReadOnlyList<T>, IDisposable
{
    private ImmutableArray<T> _list = ImmutableArray<T>.Empty;
    private readonly IDisposable _subscription;

    public SubscribedList(IObservable<T> source)
    {
        _subscription = source.Subscribe(x => _list = _list.Add(x));
    }

    public IEnumerator<T> GetEnumerator()
    {
        return ((IEnumerable<T>)_list).GetEnumerator();
    }

    IEnumerator IEnumerable.GetEnumerator() => GetEnumerator();

    public int Count => _list.Length;

    public T this[int index] => _list[index];

    public void Dispose() => _subscription.Dispose();
}
