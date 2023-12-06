// Copyright (c) Microsoft Corporation. All rights reserved.
// SequentialGroupChat.cs

using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using AutoGen.Extension;
using Microsoft.SemanticKernel.AI.ChatCompletion;

namespace AutoGen
{
    public class SequentialGroupChat : IGroupChat
    {
        private readonly List<IAgent> agents = new List<IAgent>();
        private readonly List<ChatMessage> initializeMessages = new List<ChatMessage>();

        public SequentialGroupChat(
            IEnumerable<IAgent> agents,
            List<ChatMessage>? initializeMessages = null)
        {
            this.agents.AddRange(agents);
            this.initializeMessages = initializeMessages ?? new List<ChatMessage>();
        }

        public void AddInitializeMessage(ChatMessage message)
        {
            this.initializeMessages.Add(message);
        }

        public async Task<IEnumerable<ChatMessage>> CallAsync(
            IEnumerable<ChatMessage>? conversationWithName = null,
            int maxRound = 10,
            bool throwExceptionWhenMaxRoundReached = false,
            CancellationToken? ct = null)
        {
            var conversationHistory = new List<ChatMessage>();
            if (conversationWithName != null)
            {
                conversationHistory.AddRange(conversationWithName);
            }

            var lastSpeaker = conversationHistory.LastOrDefault()?.GetFrom() switch
            {
                null => this.agents.First(),
                _ => this.agents.FirstOrDefault(x => x.Name == conversationHistory.Last().GetFrom()) ?? throw new Exception("The agent is not in the group chat"),
            };
            var round = 0;
            while (round < maxRound)
            {
                var currentSpeaker = this.SelectNextSpeaker(lastSpeaker);
                var processedConversation = this.ProcessConversationForAgent(this.initializeMessages, conversationHistory);
                var result = await currentSpeaker.GenerateReplyAsync(processedConversation) ?? throw new Exception("No result is returned.");
                conversationHistory.Add(result);

                // if message is terminate message, then terminate the conversation
                if (result?.IsGroupChatTerminateMessage() ?? false)
                {
                    break;
                }

                lastSpeaker = currentSpeaker;
                round++;
            }

            if (round == maxRound && throwExceptionWhenMaxRoundReached)
            {
                throw new Exception("Max round reached");
            }

            return conversationHistory;
        }

        private IAgent SelectNextSpeaker(IAgent currentSpeaker)
        {
            var index = this.agents.IndexOf(currentSpeaker);
            if (index == -1)
            {
                throw new ArgumentException("The agent is not in the group chat", nameof(currentSpeaker));
            }

            var nextIndex = (index + 1) % this.agents.Count;
            return this.agents[nextIndex];
        }
    }
}
