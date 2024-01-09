// Copyright (c) Microsoft Corporation. All rights reserved.
// IAgent.cs

using System.Collections.Generic;
using System.Threading;
using System.Threading.Tasks;

namespace AutoGen
{
    public interface IAgent
    {
        public string? Name { get; }

        public IChatLLM? ChatLLM { get; }

        public Task<Message> GenerateReplyAsync(IEnumerable<Message> messages, CancellationToken cancellationToken = default);
    }
}
