// Copyright (c) Microsoft Corporation. All rights reserved.
// GroupChat.cs

using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.SemanticKernel;
using Microsoft.SemanticKernel.ChatCompletion;
using Microsoft.SemanticKernel.Connectors.OpenAI;

namespace AutoGen
{
    public class GroupChat : IGroupChat
    {
        private IAgent admin;
        private List<IAgent> agents = new List<IAgent>();
        private IEnumerable<Message> initializeMessages = new List<Message>();

        public IEnumerable<Message>? Messages { get; private set; }

        public GroupChat(
            IAgent admin,
            IEnumerable<IAgent> agents,
            IEnumerable<Message>? initializeMessages = null)
        {
            this.admin = admin;
            this.agents = agents.ToList();
            this.agents.Add(admin);
            this.initializeMessages = initializeMessages ?? new List<Message>();

            this.Validation();
        }

        private void Validation()
        {
            // check if all agents has a name
            if (this.agents.Any(x => string.IsNullOrEmpty(x.Name)))
            {
                throw new Exception("All agents must have a name.");
            }

            // check if any agents has the same name
            var names = this.agents.Select(x => x.Name).ToList();
            if (names.Distinct().Count() != names.Count)
            {
                throw new Exception("All agents must have a unique name.");
            }

            // check if admin has a chat completion
            if (this.admin.ChatCompletion == null)
            {
                throw new Exception("Admin must have a chat completion.");
            }
        }

        public async Task<IAgent?> SelectNextSpeakerAsync(IEnumerable<Message> conversationHistory)
        {
            var llm = this.admin.ChatCompletion ?? throw new Exception("Admin does not have a chat completion.");
            var agent_names = this.agents.Select(x => x.Name).ToList();
            var systemMessage = new Message(Role.System,
                content: $@"You are in a role play game. Carefully read the conversation history and carry on the conversation.
The available roles are:
{string.Join(",", agent_names)}

Each message will start with 'From name:', e.g:
From admin:
//your message//.");

            var conv = this.ProcessConversationsForRolePlay(this.initializeMessages, conversationHistory);

            var messages = new Message[] { systemMessage }.Concat(conv);
            var settings = new OpenAIPromptExecutionSettings
            {
                Temperature = 0,
                StopSequences = new[]
                {
                    ":",
                },
                ExtensionData = new Dictionary<string, object>
                {
                    { "temperature", 0 },
                    { "stopWords", new[] { ":" } },
                },
            };
            var history = new ChatHistory();
            foreach (var message in messages)
            {
                history.Add(new ChatMessageContent(new AuthorRole(message.Role.ToString()), message.Content));
            }

            var response = await llm.GetChatMessageContentAsync(history, settings);

            var name = response?.Content ?? throw new Exception("No name is returned.");

            try
            {
                // remove From
                name = name!.Substring(5);
                var agent = this.agents.FirstOrDefault(x => x.Name!.ToLower() == name.ToLower());

                return agent;
            }
            catch (Exception)
            {
                return null;
            }
        }

        public void AddInitializeMessage(Message message)
        {
            this.initializeMessages = this.initializeMessages.Append(message);
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
                var currentSpeaker = await this.SelectNextSpeakerAsync(conversationHistory) ?? this.admin;
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
    }
}
