// Copyright (c) Microsoft Corporation. All rights reserved.
// IGroupChat.cs

using System.Collections.Generic;
using System.Threading;
using System.Threading.Tasks;

namespace AutoGen;

public interface IGroupChat
{
    void AddInitializeMessage(Message message);

    Task<IEnumerable<Message>> CallAsync(IEnumerable<Message>? conversation = null, int maxRound = 10, CancellationToken ct = default);
}
