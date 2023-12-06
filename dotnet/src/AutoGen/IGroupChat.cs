// Copyright (c) Microsoft Corporation. All rights reserved.
// IGroupChat.cs

using System.Collections.Generic;
using System.Threading.Tasks;
using System.Threading;
using Microsoft.SemanticKernel.AI.ChatCompletion;

namespace AutoGen
{
    public interface IGroupChat
    {
        void AddInitializeMessage(ChatMessage message);

        Task<IEnumerable<ChatMessage>> CallAsync(IEnumerable<ChatMessage>? conversationWithName = null, int maxRound = 10, bool throwExceptionWhenMaxRoundReached = true, CancellationToken? ct = null);
    }
}
