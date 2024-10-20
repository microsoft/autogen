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

namespace AutoGen.WebAPI.Tests;

public class EchoAgent : IStreamingAgent
{
    public EchoAgent(string name)
    {
        Name = name;
    }
    public string Name { get; }

    public async Task<IMessage> GenerateReplyAsync(
        IEnumerable<IMessage> messages,
        GenerateReplyOptions? options = null,
        CancellationToken cancellationToken = default)
    {
        return messages.Last();
    }

    public async IAsyncEnumerable<IMessage> GenerateStreamingReplyAsync(
        IEnumerable<IMessage> messages,
        GenerateReplyOptions? options = null,
        [EnumeratorCancellation] CancellationToken cancellationToken = default)
    {
        var lastMessage = messages.LastOrDefault();
        if (lastMessage == null)
        {
            yield break;
        }

        // return each character of the last message as a separate message
        if (lastMessage.GetContent() is string content)
        {
            foreach (var c in content)
            {
                yield return new TextMessageUpdate(Role.Assistant, c.ToString(), this.Name);
            }
        }
    }
}
