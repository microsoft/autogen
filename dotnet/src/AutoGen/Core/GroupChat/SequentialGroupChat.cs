// Copyright (c) Microsoft Corporation. All rights reserved.
// SequentialGroupChat.cs

using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;

namespace AutoGen
{
    public class SequentialGroupChat : IGroupChat
    {
        private readonly List<IAgent> agents = new List<IAgent>();
        private readonly List<Message> initializeMessages = new List<Message>();

        public SequentialGroupChat(
            IEnumerable<IAgent> agents,
            List<Message>? initializeMessages = null)
        {
            this.agents.AddRange(agents);
            this.initializeMessages = initializeMessages ?? new List<Message>();
        }

        public void AddInitializeMessage(Message message)
        {
            this.initializeMessages.Add(message);
        }

        public async Task<IEnumerable<Message>> CallAsync(
            IEnumerable<Message>? conversationWithName = null,
            int maxRound = 10,
            CancellationToken ct = default)
        {
            var conversationHistory = new List<Message>();
            if (conversationWithName != null)
            {
                conversationHistory.AddRange(conversationWithName);
            }

            var lastSpeaker = conversationHistory.LastOrDefault()?.From switch
            {
                null => this.agents.First(),
                _ => this.agents.FirstOrDefault(x => x.Name == conversationHistory.Last().From) ?? throw new Exception("The agent is not in the group chat"),
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
