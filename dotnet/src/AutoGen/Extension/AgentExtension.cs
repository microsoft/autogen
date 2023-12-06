// Copyright (c) Microsoft Corporation. All rights reserved.
// AgentExtension.cs

using Microsoft.SemanticKernel.AI.ChatCompletion;
using System.Collections.Generic;
using System.Threading.Tasks;
using System.Threading;
using System;
using Azure.AI.OpenAI;
using AutoGen.Extension;
using ChatMessage = Microsoft.SemanticKernel.AI.ChatCompletion.ChatMessage;

namespace AutoGen
{
    public static class AgentExtension
    {
        /// <summary>
        /// Send message to another agent.
        /// </summary>
        /// <param name="agent">sender agent.</param>
        /// <param name="receiver">receiver agent.</param>
        /// <param name="chatHistory">chat history.</param>
        /// <param name="maxRound">max conversation round.</param>
        /// <returns>conversation history</returns>
        public static async Task<IEnumerable<ChatMessage>> SendAsync(
            this IAgent agent,
            IAgent receiver,
            IEnumerable<ChatMessage> chatHistory,
            int maxRound = 10,
            CancellationToken? ct = default)
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
        public static async Task<IEnumerable<ChatMessage>> ReceiveAsync(
            this IAgent agent,
            IAgent sender,
            IEnumerable<ChatMessage> chatHistory,
            int maxRound = 10,
            CancellationToken? ct = default)
        {
            throw new System.NotImplementedException();
        }

        public static IAgent RegisterReply(
            this IAgent agent,
            Func<IEnumerable<ChatMessage>, CancellationToken?, Task<ChatMessage?>> replyFunc)
        {
            throw new System.NotImplementedException();
        }

        internal static IEnumerable<ChatMessage> ProcessMessages(this IAgent agent, IEnumerable<ChatMessage> messages)
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
                    yield return new ChatMessage(AuthorRole.User, content);
                }
                else if (message is ChatMessage)
                {
                    if (message.GetFunctionCall() is FunctionCall functionCall)
                    {
                        var functionCallMessage = new ChatMessage(AuthorRole.Assistant, null);
                        functionCallMessage.SetFunctionCall(functionCall);

                        i++;

                        yield return functionCallMessage;

                        var functionResultMessage = new ChatMessage(AuthorRole.Function, message.Content);

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

                        var assistantMessage = new ChatMessage(AuthorRole.Assistant, content);

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
                    yield return new ChatMessage(AuthorRole.Assistant, content);
                }
            }
        }

    }
}
