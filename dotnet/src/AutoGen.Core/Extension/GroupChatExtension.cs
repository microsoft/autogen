// Copyright (c) Microsoft Corporation. All rights reserved.
// GroupChatExtension.cs

using System;
using System.Collections.Generic;
using System.Linq;

namespace AutoGen.Core;

public static class GroupChatExtension
{
    public const string TERMINATE = "[GROUPCHAT_TERMINATE]";
    public const string CLEAR_MESSAGES = "[GROUPCHAT_CLEAR_MESSAGES]";

    [Obsolete("please use SendIntroduction")]
    public static void AddInitializeMessage(this IAgent agent, string message, IGroupChat groupChat)
    {
        var msg = new TextMessage(Role.User, message)
        {
            From = agent.Name
        };

        groupChat.SendIntroduction(msg);
    }

    /// <summary>
    /// Send an instruction message to the group chat.
    /// </summary>
    public static void SendIntroduction(this IAgent agent, string message, IGroupChat groupChat)
    {
        var msg = new TextMessage(Role.User, message)
        {
            From = agent.Name
        };

        groupChat.SendIntroduction(msg);
    }

    public static IEnumerable<IMessage> MessageToKeep(
        this IGroupChat _,
        IEnumerable<IMessage> messages)
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
    /// Return true if <see cref="IMessage"/> contains <see cref="TERMINATE"/>, otherwise false.
    /// </summary>
    /// <param name="message"></param>
    /// <returns></returns>
    public static bool IsGroupChatTerminateMessage(this IMessage message)
    {
        return message.GetContent()?.Contains(TERMINATE) ?? false;
    }

    public static bool IsGroupChatClearMessage(this IMessage message)
    {
        return message.GetContent()?.Contains(CLEAR_MESSAGES) ?? false;
    }

    public static IEnumerable<IMessage> ProcessConversationForAgent(
        this IGroupChat groupChat,
        IEnumerable<IMessage> initialMessages,
        IEnumerable<IMessage> messages)
    {
        messages = groupChat.MessageToKeep(messages);
        return initialMessages.Concat(messages);
    }

    internal static IEnumerable<IMessage> ProcessConversationsForRolePlay(
            this IGroupChat groupChat,
            IEnumerable<IMessage> initialMessages,
            IEnumerable<IMessage> messages)
    {
        messages = groupChat.MessageToKeep(messages);
        var messagesToKeep = initialMessages.Concat(messages);

        return messagesToKeep.Select((x, i) =>
        {
            var msg = @$"From {x.From}:
{x.GetContent()}
<eof_msg>
round # {i}";

            return new TextMessage(Role.User, content: msg);
        });
    }
}
