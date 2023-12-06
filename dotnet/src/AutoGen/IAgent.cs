// Copyright (c) Microsoft Corporation. All rights reserved.
// IAgent.cs

using System.Collections.Generic;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.SemanticKernel.AI.ChatCompletion;

namespace AutoGen
{
    public interface IAgent
    {
        public string Name { get; }

        public Task<ChatMessage> GenerateReplyAsync(IEnumerable<ChatMessage> messages, CancellationToken? cancellationToken = null);
    }
}
