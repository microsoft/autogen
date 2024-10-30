// Copyright (c) Microsoft. All rights reserved.

using System.Collections.Concurrent;

namespace Marketing.Backend.Hubs;

public static class SignalRConnectionsDB
{
    public static ConcurrentDictionary<string, string> ConnectionIdByUser { get; } = new ConcurrentDictionary<string, string>();
    public static ConcurrentDictionary<string, string> AllConnections { get; } = new ConcurrentDictionary<string, string>();

}
