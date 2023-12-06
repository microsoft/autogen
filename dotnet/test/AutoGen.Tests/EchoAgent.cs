// Copyright (c) Microsoft Corporation. All rights reserved.
// EchoAgent.cs

using System.Collections.Generic;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using AutoGen.Extension;
using Microsoft.SemanticKernel.AI.ChatCompletion;

namespace AutoGen.Tests
{
    internal class EchoAgent : IAgent
    {
        public EchoAgent(string name)
        {
            Name = name;
        }
        public string Name { get; }

        public IChatCompletion? ChatCompletion => null;

        public Task<Message> GenerateReplyAsync(IEnumerable<Message> conversation, CancellationToken ct = default)
        {
            // return the most recent message
            var lastMessage = conversation.Last();
            lastMessage.SetFrom(this.Name);

            return Task.FromResult<Message>(lastMessage);
        }
    }
}
