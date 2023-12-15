// Copyright (c) Microsoft Corporation. All rights reserved.
// AgentExtension.cs

using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;

namespace AutoGen
{
    public static class AgentExtension
    {
        /// <summary>
        /// Send message to an agent.
        /// </summary>
        /// <param name="agent">sender agent.</param>
        /// <param name="receiver">receiver agent.</param>
        /// <param name="chatHistory">chat history.</param>
        /// <param name="maxRound">max conversation round.</param>
        /// <returns>conversation history</returns>
        public static async Task<Message> SendAsync(
            this IAgent agent,
            Message? message = null,
            IEnumerable<Message>? chatHistory = null,
            CancellationToken ct = default)
        {
            var messages = new List<Message>();

            if (message != null)
            {
                messages.Add(message);
            }

            if (chatHistory != null)
            {
                messages.AddRange(chatHistory);
            }

            var result = await agent.GenerateReplyAsync(messages, ct);

            return result;
        }

        /// <summary>
        /// Send message to an agent.
        /// </summary>
        /// <param name="agent">sender agent.</param>
        /// <param name="receiver">receiver agent.</param>
        /// <param name="chatHistory">chat history.</param>
        /// <param name="maxRound">max conversation round.</param>
        /// <returns>conversation history</returns>
        public static async Task<Message> SendAsync(
            this IAgent agent,
            string message,
            IEnumerable<Message>? chatHistory = null,
            CancellationToken ct = default)
        {
            var msg = new Message(Role.User, message);

            return await agent.SendAsync(msg, chatHistory, ct);
        }

        /// <summary>
        /// Send message to another agent.
        /// </summary>
        /// <param name="agent">sender agent.</param>
        /// <param name="receiver">receiver agent.</param>
        /// <param name="chatHistory">chat history.</param>
        /// <param name="maxRound">max conversation round.</param>
        /// <returns>conversation history</returns>
        public static async Task<IEnumerable<Message>> SendAsync(
            this IAgent agent,
            IAgent receiver,
            IEnumerable<Message> chatHistory,
            int maxRound = 10,
            CancellationToken ct = default)
        {
            if (receiver is GroupChatManager manager)
            {
                var gc = manager.GroupChat;

                return await agent.SendMessageToGroupAsync(gc, chatHistory, maxRound, ct);
            }

            var groupChat = new SequentialGroupChat(
                agents: new[]
                {
                    agent,
                    receiver,
                });

            return await groupChat.CallAsync(chatHistory, maxRound, ct: ct);
        }

        /// <summary>
        /// Send message to another agent.
        /// </summary>
        /// <param name="agent">sender agent.</param>
        /// <param name="receiver">receiver agent.</param>
        /// <param name="chatHistory">chat history.</param>
        /// <param name="maxRound">max conversation round.</param>
        /// <returns>conversation history</returns>
        public static async Task<IEnumerable<Message>> SendAsync(
            this IAgent agent,
            IAgent receiver,
            string? message = null,
            IEnumerable<Message>? chatHistory = null,
            int maxRound = 10,
            CancellationToken ct = default)
        {
            if (message != null)
            {
                var msg = new Message(Role.User, message)
                {
                    From = agent.Name,
                };

                chatHistory = new[] { msg }.Concat(chatHistory ?? Enumerable.Empty<Message>());
            }
            else
            {
                chatHistory = chatHistory ?? Enumerable.Empty<Message>();
            }

            return await agent.SendAsync(receiver, chatHistory, maxRound, ct);
        }

        public static async Task<IEnumerable<Message>> SendMessageToGroupAsync(
            this IAgent agent,
            IGroupChat groupChat,
            string msg,
            IEnumerable<Message>? chatHistory = null,
            int maxRound = 10,
            CancellationToken ct = default)
        {
            var chatMessage = new Message(Role.Assistant, msg, from: agent.Name);
            chatHistory = new[] { chatMessage }.Concat(chatHistory ?? Enumerable.Empty<Message>());

            return await agent.SendMessageToGroupAsync(groupChat, chatHistory, maxRound, ct);
        }

        public static async Task<IEnumerable<Message>> SendMessageToGroupAsync(
            this IAgent agent,
            IGroupChat groupChat,
            IEnumerable<Message>? chatHistory = null,
            int maxRound = 10,
            CancellationToken ct = default)
        {
            return await groupChat.CallAsync(chatHistory, maxRound, ct);
        }



        /// <summary>
        /// Receive message from another agent.
        /// </summary>
        /// <param name="agent">receiver agent.</param>
        /// <param name="sender">sender agent.</param>
        /// <param name="chatHistory">chat history.</param>
        /// <param name="maxRound">max conversation round.</param>
        /// <returns></returns>
        /// <exception cref="System.NotImplementedException"></exception>
        public static async Task<IEnumerable<Message>> ReceiveAsync(
            this IAgent agent,
            IAgent sender,
            IEnumerable<Message> chatHistory,
            int maxRound = 10,
            CancellationToken? ct = default)
        {
            throw new System.NotImplementedException();
        }

        public static IAgent RegisterReply(
            this IAgent agent,
            Func<IEnumerable<Message>, CancellationToken, Task<Message?>> replyFunc)
        {
            if (agent.Name == null)
            {
                throw new Exception("Agent name is null.");
            }

            return new AutoReplyAgent(agent, agent.Name, replyFunc);
        }
    }
}
