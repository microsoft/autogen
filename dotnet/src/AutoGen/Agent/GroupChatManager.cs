// Copyright (c) Microsoft Corporation. All rights reserved.
// GroupChatManager.cs

using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.SemanticKernel.AI.ChatCompletion;

namespace AutoGen
{
    public class GroupChatManager : IAgent
    {
        private readonly IGroupChat _groupChat;

        public GroupChatManager(IGroupChat groupChat)
        {
            _groupChat = groupChat;
        }
        public string? Name => throw new ArgumentException("GroupChatManager does not have a name");

        public IChatCompletion? ChatCompletion => null;

        public async Task<Message> GenerateReplyAsync(IEnumerable<Message> messages, CancellationToken cancellationToken = default)
        {
            var response = await _groupChat.CallAsync(messages, ct: cancellationToken);

            return response.Last();
        }
    }
}
