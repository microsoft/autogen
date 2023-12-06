// Copyright (c) Microsoft Corporation. All rights reserved.
// GroupChat.cs

using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.SemanticKernel.AI;
using Microsoft.SemanticKernel.AI.ChatCompletion;

namespace AutoGen
{
    public class GroupChat : IGroupChat
    {
        private IChatCompletion chatLLM;
        private IAgent admin;
        private List<IAgent> agents = new List<IAgent>();
        private IEnumerable<ChatMessage> initializeMessages = new List<ChatMessage>();

        public GroupChat(
            IChatCompletion chatLLM,
            IAgent admin,
            IEnumerable<IAgent> agents,
            IEnumerable<ChatMessage>? initializeMessages = null)
        {
            this.chatLLM = chatLLM;
            this.admin = admin;
            this.agents = agents.ToList();
            this.agents.Add(admin);
            this.initializeMessages = initializeMessages ?? new List<ChatMessage>();
        }

        public async Task<IAgent?> SelectNextSpeakerAsync(IEnumerable<ChatMessage> conversationHistory)
        {
            var agent_names = this.agents.Select(x => x.Name).ToList();
            var systemMessage = new ChatMessage(AuthorRole.System,
                content: $@"You are in a role play game. Carefully read the conversation history and carry on the conversation.
The available roles are:
{string.Join(",", agent_names)}

Each message will start with 'From name:', e.g:
From admin:
//your message//.");

            var conv = this.ProcessConversationsForRolePlay(this.initializeMessages, conversationHistory);

            var messages = new ChatMessage[] { systemMessage }.Concat(conv);
            var settings = new AIRequestSettings
            {
                ExtensionData = new Dictionary<string, object>
                {
                    { "temperature", 0 },
                    { "stopWords", new[] { ":" } },
                },
            };
            var history = this.chatLLM.CreateNewChat();
            foreach (var message in messages)
            {
                history.Add(message);
            }

            var response = await this.chatLLM.GenerateMessageAsync(history, settings);

            var name = response ?? throw new Exception("No name is returned.");

            try
            {
                // remove From
                name = name!.Substring(5);
                var agent = this.agents.FirstOrDefault(x => x.Name.ToLower() == name.ToLower());

                return agent;
            }
            catch (Exception)
            {
                return null;
            }
        }

        public void AddInitializeMessage(ChatMessage message)
        {
            this.initializeMessages = this.initializeMessages.Append(message);
        }

        public async Task<IEnumerable<ChatMessage>> CallAsync(
            IEnumerable<ChatMessage>? conversationWithName = null,
            int maxRound = 10,
            bool throwExceptionWhenMaxRoundReached = false,
            CancellationToken? ct = null)
        {
            if (maxRound == 0)
            {
                if (throwExceptionWhenMaxRoundReached)
                {
                    throw new Exception("Max round reached.");
                }
                else
                {
                    return conversationWithName ?? Enumerable.Empty<ChatMessage>();
                }
            }

            // sleep 10 seconds
            await Task.Delay(1000);

            if (conversationWithName == null)
            {
                conversationWithName = Enumerable.Empty<ChatMessage>();
            }

            var agent = await this.SelectNextSpeakerAsync(conversationWithName) ?? this.admin;
            var processedConversation = this.ProcessConversationForAgent(this.initializeMessages, conversationWithName);
            var result = await agent.GenerateReplyAsync(processedConversation) ?? throw new Exception("No result is returned.");
            var updatedConversation = conversationWithName.Append(result);

            // if message is terminate message, then terminate the conversation
            if (result?.IsGroupChatTerminateMessage() ?? false)
            {
                return updatedConversation;
            }

            return await this.CallAsync(updatedConversation, maxRound - 1, throwExceptionWhenMaxRoundReached);
        }
    }
}
