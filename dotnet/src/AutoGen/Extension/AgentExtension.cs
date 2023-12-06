// Copyright (c) Microsoft Corporation. All rights reserved.
// AgentExtension.cs

using System;
using System.Collections.Generic;
using System.Threading;
using System.Threading.Tasks;
using AutoGen.Extension;
using Azure.AI.OpenAI;
using Microsoft.SemanticKernel.AI.ChatCompletion;

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
            var msg = new Message(AuthorRole.User, message);

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
            throw new System.NotImplementedException();
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
            throw new System.NotImplementedException();
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
            Func<IEnumerable<Message>, CancellationToken?, Task<Message?>> replyFunc)
        {
            if (agent.Name == null)
            {
                throw new Exception("Agent name is null.");
            }

            return new AutoReplyAgent(agent, agent.Name, replyFunc);
        }

        internal static IEnumerable<Message> ProcessMessages(this IAgent agent, IEnumerable<Message> messages)
        {
            var i = 0;
            foreach (var message in messages)
            {
                if (message.GetFrom() != agent.Name)
                {
                    // add as user message
                    var content = message.Content ?? string.Empty;
                    content = @$"{content}
<eof_msg>
From {message.GetFrom()}
round # {i++}";
                    yield return new Message(AuthorRole.User, content);
                }
                else if (message is Message)
                {
                    if (message.GetFunctionCall() is FunctionCall functionCall)
                    {
                        var functionCallMessage = new Message(AuthorRole.Assistant, null);
                        functionCallMessage.SetFunctionCall(functionCall);

                        i++;

                        yield return functionCallMessage;

                        var functionResultMessage = new Message(AuthorRole.Function, message.Content);

                        functionResultMessage.SetFrom(functionCall.Name);
                        yield return functionResultMessage;

                        i++;
                    }
                    else
                    {
                        // add suffix
                        var content = message.Content ?? string.Empty;
                        content = @$"{content}
<eof_msg>
round # {i++}";

                        var assistantMessage = new Message(AuthorRole.Assistant, content);

                        yield return assistantMessage;
                    }
                }
                else
                {
                    // add as asssistant message
                    var content = message.Content ?? string.Empty;
                    content = @$"{content}
<eof_msg>
round # {i++}";
                    yield return new Message(AuthorRole.Assistant, content);
                }
            }
        }

    }
}
