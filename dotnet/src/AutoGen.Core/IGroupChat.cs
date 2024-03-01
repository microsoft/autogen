// Copyright (c) Microsoft Corporation. All rights reserved.
// IGroupChat.cs

using System.Collections.Generic;
using System.Threading;
using System.Threading.Tasks;

namespace AutoGen.Core;

public interface IGroupChat
{
    void AddInitializeMessage(IMessage message);

    Task<IEnumerable<IMessage>> CallAsync(IEnumerable<IMessage>? conversation = null, int maxRound = 10, CancellationToken ct = default);
}
