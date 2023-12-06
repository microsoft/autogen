// Copyright (c) Microsoft Corporation. All rights reserved.
// AutoReplyAgent.cs

using System;
using System.Collections.Generic;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.SemanticKernel.AI.ChatCompletion;

namespace AutoGen
{
    /// <summary>
    /// The auto-reply agent contains an inner agent and an auto-reply function.
    /// When calling into the auto-reply agent, it will first try to reply the message using the auto-reply function.
    /// If the auto-reply function returns a null value, the inner agent will be called to generate the reply message.
    /// </summary>
    public class AutoReplyAgent : IAgent
    {
        /// <summary>
        /// Create an auto-reply agent.
        /// </summary>
        /// <param name="innerAgent">the inner agent.</param>
        /// <param name="name">the name of <see cref="AutoReplyAgent"/>.</param>
        /// <param name="autoReplyFunc">auto-reply function.</param>
        public AutoReplyAgent(
            IAgent innerAgent,
            string name,
            Func<IEnumerable<Message>, CancellationToken?, Task<Message?>> autoReplyFunc)
        {
            InnerAgent = innerAgent;
            Name = name;
            AutoReplyFunc = autoReplyFunc;
        }


        /// <summary>
        /// The auto-reply function that will be called before calling <see cref="InnerAgent"/>.
        /// If the function returns a non-null value, the agent will not be called.
        /// Otherwise, the agent will be called.
        /// </summary>
        public Func<IEnumerable<Message>, CancellationToken?, Task<Message?>> AutoReplyFunc { get; }

        public string? Name { get; }

        /// <summary>
        /// The inner agent.
        /// </summary>
        public IAgent InnerAgent { get; }

        public IChatCompletion? ChatCompletion => InnerAgent.ChatCompletion;

        /// <summary>
        /// call the agent to generate reply message.
        /// It will first try to auto reply the message. If no auto reply is available, the <see cref="InnerAgent"/> will be called to generate the reply message.
        /// </summary>
        public async Task<Message> GenerateReplyAsync(IEnumerable<Message> messages, CancellationToken cancellationToken = default)
        {
            if (await AutoReplyFunc(messages, cancellationToken) is Message autoReply)
            {
                return autoReply;
            }
            else
            {
                return await InnerAgent.GenerateReplyAsync(messages, cancellationToken);
            }
        }
    }
}
