// Copyright (c) Microsoft Corporation. All rights reserved.
// AssistantAgent.cs

using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using AutoGen.Extension;
using Azure.AI.OpenAI;
using Microsoft.SemanticKernel.AI.ChatCompletion;

namespace AutoGen
{
    public class AssistantAgent : IAgent
    {
        public enum HumanInputMode
        {
            NEVER = 0,
            ALWAYS = 1,
            AUTO = 2,
        }

        private readonly IAgent? innerAgent;
        private readonly string? defaultReply;
        private readonly HumanInputMode humanInputMode;
        private readonly IDictionary<string, Func<string, Task<string>>>? functionMaps;
        private readonly bool selfExecute;

        public AssistantAgent(
            string name,
            IAgent? innerAgent = null,
            string? defaultReply = null,
            HumanInputMode humanInputMode = HumanInputMode.AUTO,
            Func<IEnumerable<Message>, CancellationToken, Task<bool>>? isTermination = null,
            IDictionary<string, Func<string, Task<string>>>? functionMaps = null,
            bool selfExecute = true)
        {
            this.Name = name;
            this.defaultReply = defaultReply;
            this.functionMaps = functionMaps;
            this.humanInputMode = humanInputMode;
            this.innerAgent = innerAgent;
            this.IsTermination = isTermination;
            this.defaultReply = defaultReply;
            this.selfExecute = selfExecute;
        }

        public string? Name { get; }

        public IChatCompletion? ChatCompletion { get; private set; }

        public Func<IEnumerable<Message>, CancellationToken, Task<bool>>? IsTermination { get; }

        public async Task<Message> GenerateReplyAsync(IEnumerable<Message> messages, CancellationToken cancellationToken = default)
        {
            // process order: function_call -> human_input -> inner_agent -> default_reply -> self_execute
            // first in, last out

            // process default reply
            IAgent agent = new DefaultReplyAgent(this.Name!, this.defaultReply);

            // process inner agent
            agent = agent.RegisterReply(async (messages, cancellationToken) =>
            {
                if (this.innerAgent != null)
                {
                    // for every message, update message.From to inner agent's name if it is the name of this assistant agent
                    var updatedMessages = messages.Select(m =>
                    {
                        if (m.From == this.Name)
                        {
                            var clone = new Message(m);
                            clone.From = this.innerAgent.Name;
                            return clone;
                        }
                        else
                        {
                            return m;
                        }
                    });

                    var msg = await this.innerAgent.GenerateReplyAsync(updatedMessages, cancellationToken);
                    msg.SetFrom(this.Name!);

                    return msg;
                }
                else
                {
                    return null;
                }
            });

            // process human input
            agent = agent.RegisterReply(async (messages, cancellationToken) =>
            {
                async Task<Message> TakeUserInputAsync()
                {
                    // first, write prompt, then read from stdin
                    var prompt = "Please give feedback: Press enter or type 'exit' to stop the conversation.";
                    Console.WriteLine(prompt);
                    var userInput = Console.ReadLine();
                    if (userInput != null && userInput.ToLower() != "exit")
                    {
                        var message = new Message(AuthorRole.Assistant, userInput, from: this.Name);
                        return message;
                    }
                    else
                    {
                        userInput = string.Empty;
                        var message = new Message(AuthorRole.Assistant, userInput, from: this.Name);
                        return message;
                    }
                }

                if (this.humanInputMode == HumanInputMode.ALWAYS)
                {
                    return await TakeUserInputAsync();
                }
                else if (this.humanInputMode == HumanInputMode.AUTO)
                {
                    if (this.IsTermination != null && await this.IsTermination(messages, cancellationToken))
                    {
                        return await TakeUserInputAsync();
                    }
                    else
                    {
                        return null;
                    }
                }
                else
                {
                    return null;
                }
            });

            // process function call
            agent = agent.RegisterReply(async (messages, cancellationToken) =>
            {
                if (this.functionMaps != null && messages.Last()?.FunctionCall is FunctionCall fc)
                {
                    return await this.ExecuteFunctionCallAsync(messages.Last(), cancellationToken);
                }

                return null;
            });

            // process self execute
            agent = new PostProcessAgent(agent, agent.Name!, async (messages, currentMessage, cancellationToken) =>
            {
                if (this.selfExecute && currentMessage.FunctionCall is FunctionCall fc)
                {
                    return await this.ExecuteFunctionCallAsync(currentMessage, cancellationToken);
                }
                else
                {
                    return currentMessage;
                }
            });

            return await agent.GenerateReplyAsync(messages, cancellationToken);
        }

        private async Task<Message> ExecuteFunctionCallAsync(Message message, CancellationToken cancellationToken)
        {
            if (this.functionMaps != null && message.FunctionCall is FunctionCall fc)
            {
                if (this.functionMaps.TryGetValue(fc.Name, out var func))
                {
                    var result = await func(fc.Arguments);
                    return new Message(AuthorRole.Assistant, result, from: this.Name)
                    {
                        FunctionCall = fc,
                    };
                }
                else
                {
                    var errorMessage = $"Function {fc.Name} is not available. Available functions are: {string.Join(", ", this.functionMaps.Select(f => f.Key))}";
                    return new Message(AuthorRole.Assistant, errorMessage, from: this.Name)
                    {
                        FunctionCall = fc,
                    };
                }
            }

            throw new Exception("Function call is not available.");
        }
    }
}
