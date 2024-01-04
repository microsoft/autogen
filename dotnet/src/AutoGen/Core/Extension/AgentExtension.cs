// Copyright (c) Microsoft Corporation. All rights reserved.
// AgentExtension.cs

using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using AutoGen.Extension;

namespace AutoGen
{
    public static class AgentExtension
    {
        /// <summary>
        /// Send message to an agent.
        /// </summary>
        /// <param name="agent">sender agent.</param>
        /// <param name="chatHistory">chat history.</param>
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
        /// <param name="chatHistory">chat history.</param>
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
            string message,
            IEnumerable<Message>? chatHistory = null,
            int maxRound = 10,
            CancellationToken ct = default)
        {
            var msg = new Message(Role.User, message)
            {
                From = agent.Name,
            };

            chatHistory = new[] { msg }.Concat(chatHistory ?? Enumerable.Empty<Message>());

            return await agent.SendAsync(receiver, chatHistory, maxRound, ct);
        }

        /// <summary>
        /// Shortcut API to send message to another agent.
        /// </summary>
        /// <param name="agent">sender agent</param>
        /// <param name="receiver">receiver agent</param>
        /// <param name="message">message to send</param>
        /// <param name="maxRound">max round</param>
        public static async Task<IEnumerable<Message>> InitiateChatAsync(
            this IAgent agent,
            IAgent receiver,
            string? message = null,
            int maxRound = 10,
            CancellationToken ct = default)
        {
            var chatHistory = new List<Message>();
            if (message != null)
            {
                var msg = new Message(Role.User, message)
                {
                    From = agent.Name,
                };

                chatHistory.Add(msg);
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
            this IAgent _,
            IGroupChat groupChat,
            IEnumerable<Message>? chatHistory = null,
            int maxRound = 10,
            CancellationToken ct = default)
        {
            return await groupChat.CallAsync(chatHistory, maxRound, ct);
        }

        /// <summary>
        /// Register a auto reply hook to an agent. The hook will be called before the agent generate the reply.
        /// If the hook return a non-null reply, then that non-null reply will be returned directly without calling the agent.
        /// Otherwise, the agent will generate the reply.
        /// This is useful when you want to override the agent reply in some cases.
        /// </summary>
        /// <param name="agent"></param>
        /// <param name="replyFunc"></param>
        /// <returns></returns>
        /// <exception cref="Exception">throw when agent name is null.</exception>
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

        /// <summary>
        /// Print formatted message to console.
        /// </summary>
        public static IAgent PrintFormatMessage(this IAgent agent)
        {
            return agent.RegisterPostProcess(async (conversation, reply, ct) =>
            {
                Console.WriteLine(reply.FormatMessage());

                return reply;
            });
        }

        /// <summary>
        /// Register a post process hook to an agent. The hook will be called before the agent return the reply and after the agent generate the reply.
        /// This is useful when you want to customize arbitrary behavior before the agent return the reply.
        /// 
        /// One example is <see cref="PrintFormatMessage(IAgent)"/>, which print the formatted message to console before the agent return the reply.
        /// </summary>
        /// <exception cref="Exception">throw when agent name is null.</exception>
        public static IAgent RegisterPostProcess(
            this IAgent agent,
            Func<IEnumerable<Message>, Message, CancellationToken, Task<Message>> postprocessFunc)
        {
            if (agent.Name == null)
            {
                throw new Exception("Agent name is null.");
            }

            return new PostProcessAgent(agent, agent.Name, postprocessFunc);
        }

        /// <summary>
        /// Register a pre process hook to an agent. The hook will be called before the agent generate the reply. This is useful when you want to modify the conversation history before the agent generate the reply.
        /// </summary>
        /// <exception cref="Exception">throw when agent name is null.</exception>
        public static IAgent RegisterPreProcess(
            this IAgent agent,
            Func<IEnumerable<Message>, CancellationToken, Task<IEnumerable<Message>>> preprocessFunc)
        {
            if (agent.Name == null)
            {
                throw new Exception("Agent name is null.");
            }

            return new PreProcessAgent(agent, agent.Name, preprocessFunc);
        }
    }
}
