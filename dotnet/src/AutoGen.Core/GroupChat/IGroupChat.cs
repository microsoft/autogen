// Copyright (c) 2023 - 2024, Owners of https://github.com/autogen-ai
// SPDX-License-Identifier: Apache-2.0
// Contributions to this project, i.e., https://github.com/autogen-ai/autogen, 
// are licensed under the Apache License, Version 2.0 (Apache-2.0).
// Portions derived from  https://github.com/microsoft/autogen under the MIT License.
// SPDX-License-Identifier: MIT
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
