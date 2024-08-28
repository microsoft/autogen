// Copyright (c) 2023 - 2024, Owners of https://github.com/autogen-ai
// SPDX-License-Identifier: Apache-2.0
// Contributions to this project, i.e., https://github.com/autogen-ai/autogen, 
// are licensed under the Apache License, Version 2.0 (Apache-2.0).
// Portions derived from  https://github.com/microsoft/autogen under the MIT License.
// SPDX-License-Identifier: MIT
// Copyright (c) Microsoft Corporation. All rights reserved.
// GroupChatManager.cs

using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;

namespace AutoGen.Core;

public class GroupChatManager : IAgent
{
    public GroupChatManager(IGroupChat groupChat)
    {
        GroupChat = groupChat;
    }
    public string Name => throw new ArgumentException("GroupChatManager does not have a name");

    public IEnumerable<IMessage>? Messages { get; private set; }

    public IGroupChat GroupChat { get; }

    public async Task<IMessage> GenerateReplyAsync(
        IEnumerable<IMessage> messages,
        GenerateReplyOptions? options,
        CancellationToken cancellationToken = default)
    {
        var response = await GroupChat.CallAsync(messages, ct: cancellationToken);
        Messages = response;

        return response.Last();
    }
}
