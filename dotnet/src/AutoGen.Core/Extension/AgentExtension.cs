// Copyright (c) Microsoft Corporation. All rights reserved.
// AgentExtension.cs

using System.Collections.Generic;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;

namespace AutoGen.Core;

public static class AgentExtension
{
    /// <summary>
    /// Send message to an agent.
    /// </summary>
    /// <param name="message">message to send. will be added to the end of <paramref name="chatHistory"/> if provided </param>
    /// <param name="agent">sender agent.</param>
    /// <param name="chatHistory">chat history.</param>
    /// <returns>conversation history</returns>
    public static async Task<IMessage> SendAsync(
        this IAgent agent,
        IMessage? message = null,
        IEnumerable<IMessage>? chatHistory = null,
        CancellationToken ct = default)
    {
        var messages = new List<IMessage>();

        if (chatHistory != null)
        {
            messages.AddRange(chatHistory);
        }

        if (message != null)
        {
            messages.Add(message);
        }


        var result = await agent.GenerateReplyAsync(messages, cancellationToken: ct);

        return result;
    }

    /// <summary>
    /// Send message to an agent.
    /// </summary>
    /// <param name="agent">sender agent.</param>
    /// <param name="message">message to send. will be added to the end of <paramref name="chatHistory"/> if provided </param>
    /// <param name="chatHistory">chat history.</param>
    /// <returns>conversation history</returns>
    public static async Task<IMessage> SendAsync(
        this IAgent agent,
        string message,
        IEnumerable<IMessage>? chatHistory = null,
        CancellationToken ct = default)
    {
        var msg = new TextMessage(Role.User, message);

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
    public static async Task<IEnumerable<IMessage>> SendAsync(
        this IAgent agent,
        IAgent receiver,
        IEnumerable<IMessage> chatHistory,
        int maxRound = 10,
        CancellationToken ct = default)
    {
        if (receiver is GroupChatManager manager)
        {
            var gc = manager.GroupChat;

            return await agent.SendMessageToGroupAsync(gc, chatHistory, maxRound, ct);
        }

        var groupChat = new RoundRobinGroupChat(
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
    /// <param name="message">message to send. will be added to the end of <paramref name="chatHistory"/> if provided </param>
    /// <param name="receiver">receiver agent.</param>
    /// <param name="chatHistory">chat history.</param>
    /// <param name="maxRound">max conversation round.</param>
    /// <returns>conversation history</returns>
    public static async Task<IEnumerable<IMessage>> SendAsync(
        this IAgent agent,
        IAgent receiver,
        string message,
        IEnumerable<IMessage>? chatHistory = null,
        int maxRound = 10,
        CancellationToken ct = default)
    {
        var msg = new TextMessage(Role.User, message)
        {
            From = agent.Name,
        };

        chatHistory = chatHistory ?? new List<IMessage>();
        chatHistory = chatHistory.Append(msg);

        return await agent.SendAsync(receiver, chatHistory, maxRound, ct);
    }

    /// <summary>
    /// Shortcut API to send message to another agent.
    /// </summary>
    /// <param name="agent">sender agent</param>
    /// <param name="receiver">receiver agent</param>
    /// <param name="message">message to send</param>
    /// <param name="maxRound">max round</param>
    public static async Task<IEnumerable<IMessage>> InitiateChatAsync(
        this IAgent agent,
        IAgent receiver,
        string? message = null,
        int maxRound = 10,
        CancellationToken ct = default)
    {
        var chatHistory = new List<IMessage>();
        if (message != null)
        {
            var msg = new TextMessage(Role.User, message)
            {
                From = agent.Name,
            };

            chatHistory.Add(msg);
        }

        return await agent.SendAsync(receiver, chatHistory, maxRound, ct);
    }

    public static async Task<IEnumerable<IMessage>> SendMessageToGroupAsync(
        this IAgent agent,
        IGroupChat groupChat,
        string msg,
        IEnumerable<IMessage>? chatHistory = null,
        int maxRound = 10,
        CancellationToken ct = default)
    {
        var chatMessage = new TextMessage(Role.Assistant, msg, from: agent.Name);
        chatHistory = chatHistory ?? Enumerable.Empty<IMessage>();
        chatHistory = chatHistory.Append(chatMessage);

        return await agent.SendMessageToGroupAsync(groupChat, chatHistory, maxRound, ct);
    }

    public static async Task<IEnumerable<IMessage>> SendMessageToGroupAsync(
        this IAgent _,
        IGroupChat groupChat,
        IEnumerable<IMessage>? chatHistory = null,
        int maxRound = 10,
        CancellationToken ct = default)
    {
        return await groupChat.CallAsync(chatHistory, maxRound, ct);
    }
}
