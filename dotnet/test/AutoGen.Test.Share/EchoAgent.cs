// Copyright (c) 2023 - 2024, Owners of https://github.com/autogenhub
// SPDX-License-Identifier: Apache-2.0
// Contributions to this project, i.e., https://github.com/autogenhub/autogen, 
// are licensed under the Apache License, Version 2.0 (Apache-2.0).
// Portions derived from  https://github.com/microsoft/autogen under the MIT License.
// SPDX-License-Identifier: MIT
// Copyright (c) Microsoft Corporation. All rights reserved.
// EchoAgent.cs

using System.Runtime.CompilerServices;
using AutoGen.Core;

namespace AutoGen.Tests;

public class EchoAgent : IStreamingAgent
{
    public EchoAgent(string name)
    {
        Name = name;
    }
    public string Name { get; }

    public Task<IMessage> GenerateReplyAsync(
        IEnumerable<IMessage> conversation,
        GenerateReplyOptions? options = null,
        CancellationToken ct = default)
    {
        // return the most recent message
        var lastMessage = conversation.Last();
        lastMessage.From = this.Name;

        return Task.FromResult(lastMessage);
    }

    public async IAsyncEnumerable<IMessage> GenerateStreamingReplyAsync(IEnumerable<IMessage> messages, GenerateReplyOptions? options = null, [EnumeratorCancellation] CancellationToken cancellationToken = default)
    {
        foreach (var message in messages)
        {
            message.From = this.Name;
            yield return message;
        }
    }
}
