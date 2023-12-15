// Copyright (c) Microsoft Corporation. All rights reserved.
// UserProxyAgent.cs

using System.Collections.Generic;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.SemanticKernel.AI.ChatCompletion;

namespace AutoGen
{
    public class UserProxyAgent : IAgent
    {
        public string? Name { get; }

        public IChatCompletion? ChatCompletion => null;

        public Task<Message> GenerateReplyAsync(IEnumerable<Message> messages, CancellationToken cancellationToken = default)
        {
            var prompt = "User: ";
            // write prompt to console
            System.Console.Write(prompt);

            // read user input
            var userInput = System.Console.ReadLine();
            if (userInput != null)
            {
                var message = new Message(AuthorRole.Assistant, userInput, from: this.Name);
                return Task.FromResult<Message>(message);
            }
            else
            {
                userInput = string.Empty;
                var message = new Message(AuthorRole.Assistant, userInput, from: this.Name);
                return Task.FromResult<Message>(message);
            }
        }
    }
}
