// Copyright (c) Microsoft Corporation. All rights reserved.
// FreePortManager.cs

using System.Diagnostics;

namespace Microsoft.AutoGen.Core.Grpc.Tests;

internal sealed class FreePortManager
{
    private HashSet<int> takenPorts = new();
    private readonly object mutex = new();

    [DebuggerDisplay($"{{{nameof(Port)}}}")]
    internal sealed class PortTicket(FreePortManager portManager, int port) : IDisposable
    {
        private FreePortManager? portManager = portManager;

        public int Port { get; } = port;

        public void Dispose()
        {
            FreePortManager? localPortManager = Interlocked.Exchange(ref this.portManager, null);
            localPortManager?.takenPorts.Remove(this.Port);
        }

        public override string ToString()
        {
            return this.Port.ToString();
        }

        public override bool Equals(object? obj)
        {
            return obj is PortTicket ticket && ticket.Port == this.Port;
        }

        public override int GetHashCode()
        {
            return this.Port.GetHashCode();
        }

        public static implicit operator int(PortTicket ticket) => ticket.Port;
        public static implicit operator string(PortTicket ticket) => ticket.ToString();
    }

    public PortTicket GetAvailablePort()
    {
        lock (mutex)
        {
            int port;
            do
            {
                using var listener = new System.Net.Sockets.TcpListener(System.Net.IPAddress.Loopback, 0);
                listener.Start();
                port = ((System.Net.IPEndPoint)listener.LocalEndpoint).Port;
                listener.Stop();
                listener.Dispose();
                Thread.Yield(); // Let the listener actually shut down before we try to use the port
            } while (takenPorts.Contains(port));

            takenPorts.Add(port);

            Console.WriteLine($"FreePortManager: Yielding port {port}");
            Debug.WriteLine($"FreePortManager: Yielding port {port}");
            return new PortTicket(this, port);
        }
    }
}
