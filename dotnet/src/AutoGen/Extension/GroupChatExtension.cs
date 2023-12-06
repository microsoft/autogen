// Copyright (c) Microsoft Corporation. All rights reserved.
// GroupChatExtension.cs

using System.Collections.Generic;
using System.Linq;
using AutoGen.Extension;
using Microsoft.SemanticKernel.AI.ChatCompletion;

namespace AutoGen
{
    public static class GroupChatExtension
    {
        public const string TERMINATE = "[GROUPCHAT_TERMINATE]";
        public const string CLEAR_MESSAGES = "[GROUPCHAT_CLEAR_MESSAGES]";

        public static void AddInitializeMessage(this IAgent agent, string message, IGroupChat groupChat)
        {
            var msg = new ChatMessage(AuthorRole.User, message);
            msg.SetFrom(agent.Name);

            groupChat.AddInitializeMessage(msg);
        }

        public static IEnumerable<ChatMessage> MessageToKeep(
            this IGroupChat _,
            IEnumerable<ChatMessage> messages)
        {
            var lastCLRMessageIndex = messages.ToList()
                    .FindLastIndex(x => x.IsGroupChatClearMessage());

            // if multiple clr messages, e.g [msg, clr, msg, clr, msg, clr, msg]
            // only keep the the messages after the second last clr message.
            if (messages.Count(m => m.IsGroupChatClearMessage()) > 1)
            {
                lastCLRMessageIndex = messages.ToList()
                    .FindLastIndex(lastCLRMessageIndex - 1, lastCLRMessageIndex - 1, x => x.IsGroupChatClearMessage());
                messages = messages.Skip(lastCLRMessageIndex);
            }

            lastCLRMessageIndex = messages.ToList()
                .FindLastIndex(x => x.IsGroupChatClearMessage());

            if (lastCLRMessageIndex != -1 && messages.Count() - lastCLRMessageIndex >= 2)
            {
                messages = messages.Skip(lastCLRMessageIndex);
            }

            return messages;
        }

        /// <summary>
        /// Return true if <see cref="ChatMessage.Content"/> contains <see cref="TERMINATE"/>, otherwise false.
        /// </summary>
        /// <param name="message"></param>
        /// <returns></returns>
        public static bool IsGroupChatTerminateMessage(this ChatMessage message)
        {
            return message.Content?.Contains(TERMINATE) ?? false;
        }

        public static bool IsGroupChatClearMessage(this ChatMessage message)
        {
            return message.Content?.Contains(CLEAR_MESSAGES) ?? false;
        }

        public static IEnumerable<ChatMessage> ProcessConversationForAgent(
            this IGroupChat groupChat,
            IEnumerable<ChatMessage> initialMessages,
            IEnumerable<ChatMessage> messages)
        {
            messages = groupChat.MessageToKeep(messages);
            return initialMessages.Concat(messages);
        }

        internal static IEnumerable<ChatMessage> ProcessConversationsForRolePlay(
                this IGroupChat groupChat,
                IEnumerable<ChatMessage> initialMessages,
                IEnumerable<ChatMessage> messages)
        {
            messages = groupChat.MessageToKeep(messages);
            var messagesToKeep = initialMessages.Concat(messages);

            return messagesToKeep.Select((x, i) =>
            {
                var msg = @$"From {x.From}:
{x.Content}
<eof_msg>
round # 
                {i}";

                return new ChatMessage(AuthorRole.User, content: msg);
            });
        }
    }
}
