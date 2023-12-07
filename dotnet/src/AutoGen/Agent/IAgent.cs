// Copyright (c) Microsoft Corporation. All rights reserved.
// IAgent.cs

using System.Collections.Generic;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.SemanticKernel.AI.ChatCompletion;

namespace AutoGen
{
    public delegate Task<string> FunctionExecutor(string args);

    public interface IAgent
    {
        public string? Name { get; }

        public IChatCompletion? ChatCompletion { get; }

        public Task<Message> GenerateReplyAsync(IEnumerable<Message> messages, CancellationToken cancellationToken = default);
    }
}
