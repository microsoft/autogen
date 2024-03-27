// Copyright (c) Microsoft Corporation. All rights reserved.
// IGroupChat.cs

using System;
using System.Collections.Generic;
using System.Threading;
using System.Threading.Tasks;

namespace AutoGen.Core;

public interface IGroupChat
{
    /// <summary>
    /// Send an introduction message to the group chat.
    /// </summary>
    void SendIntroduction(IMessage message);

    [Obsolete("please use SendIntroduction")]
    void AddInitializeMessage(IMessage message);

    Task<IEnumerable<IMessage>> CallAsync(IEnumerable<IMessage>? conversation = null, int maxRound = 10, CancellationToken ct = default);
}
