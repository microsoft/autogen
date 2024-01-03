// Copyright (c) Microsoft Corporation. All rights reserved.
// PostProcessAgent.cs

using System;
using System.Collections.Generic;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.SemanticKernel.ChatCompletion;

namespace AutoGen
{
    public class PostProcessAgent : IAgent
    {
        public PostProcessAgent(
            IAgent innerAgent,
            string name,
            Func<IEnumerable<Message>, Message, CancellationToken, Task<Message>> postprocessFunc)
        {
            InnerAgent = innerAgent;
            Name = name;
            PostprocessFunc = postprocessFunc;
        }

        public IAgent InnerAgent { get; }

        public string Name { get; }

        public Func<IEnumerable<Message>, Message, CancellationToken, Task<Message>> PostprocessFunc { get; }

        public IChatCompletionService? ChatCompletion => InnerAgent.ChatCompletion;

        public async Task<Message> GenerateReplyAsync(IEnumerable<Message> conversation, CancellationToken ct = default)
        {
            var reply = await InnerAgent.GenerateReplyAsync(conversation, ct);
            return await PostprocessFunc(conversation, reply, ct);
        }
    }
}
