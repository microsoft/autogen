// Copyright (c) Microsoft Corporation. All rights reserved.
// EchoAgent.cs

using System.Collections.Generic;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;

namespace AutoGen.Tests
{
    internal class EchoAgent : IAgent
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
    }
}
