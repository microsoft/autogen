// Copyright (c) Microsoft Corporation. All rights reserved.
// DefaultReplyAgent.cs

using System.Collections.Generic;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.SemanticKernel.AI.ChatCompletion;

namespace AutoGen
{
    public class DefaultReplyAgent : IAgent
    {
        public DefaultReplyAgent(
            string name,
            string? defaultReply)
        {
            Name = name;
            DefaultReply = defaultReply;
        }

        public string Name { get; }

        public string DefaultReply { get; } = string.Empty;

        public IChatCompletion? ChatCompletion => null;

        public async Task<Message> GenerateReplyAsync(IEnumerable<Message> conversation, CancellationToken ct = default)
        {
            return new Message(Role.Assistant, DefaultReply, from: this.Name);
        }
    }
}
