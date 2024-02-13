// Copyright (c) Microsoft Corporation. All rights reserved.
// ConversableAgent.cs

using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using AutoGen.OpenAI;

namespace AutoGen;

public class ConversableAgent : IAgent
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
    private readonly IDictionary<string, Func<string, Task<string>>>? functionMap;
    private readonly string systemMessage;

    public ConversableAgent(
        string name,
        string systemMessage = "You are a helpful AI assistant",
        IAgent? innerAgent = null,
        string? defaultAutoReply = null,
        HumanInputMode humanInputMode = HumanInputMode.NEVER,
        Func<IEnumerable<Message>, CancellationToken, Task<bool>>? isTermination = null,
        IDictionary<string, Func<string, Task<string>>>? functionMap = null)
    {
        this.Name = name;
        this.defaultReply = defaultAutoReply;
        this.functionMap = functionMap;
        this.humanInputMode = humanInputMode;
        this.innerAgent = innerAgent;
        this.IsTermination = isTermination;
        this.defaultReply = defaultAutoReply;
        this.systemMessage = systemMessage;
    }

    public ConversableAgent(
        string name,
        string systemMessage = "You are a helpful AI assistant",
        ConversableAgentConfig? llmConfig = null,
        Func<IEnumerable<Message>, CancellationToken, Task<bool>>? isTermination = null,
        HumanInputMode humanInputMode = HumanInputMode.AUTO,
        IDictionary<string, Func<string, Task<string>>>? functionMap = null,
        string? defaultReply = null)
    {
        this.Name = name;
        this.defaultReply = defaultReply;
        this.functionMap = functionMap;
        this.humanInputMode = humanInputMode;
        this.IsTermination = isTermination;
        this.systemMessage = systemMessage;
        this.innerAgent = llmConfig?.ConfigList != null ? this.CreateInnerAgentFromConfigList(llmConfig) : null;
    }

    /// <summary>
    /// Override this method to change the behavior of getting human input
    /// </summary>
    public virtual Task<string?> GetHumanInputAsync()
    {
        // first, write prompt, then read from stdin
        var prompt = "Please give feedback: Press enter or type 'exit' to stop the conversation.";
        Console.WriteLine(prompt);
        var userInput = Console.ReadLine();
        if (!string.IsNullOrEmpty(userInput) && userInput.ToLower() != "exit")
        {
            return Task.FromResult<string?>(userInput);
        }
        else
        {
            Console.WriteLine("Terminating the conversation");
            userInput = GroupChatExtension.TERMINATE;
            return Task.FromResult<string?>(userInput);
        }
    }

    private IAgent? CreateInnerAgentFromConfigList(ConversableAgentConfig config)
    {
        IAgent? agent = null;
        foreach (var llmConfig in config.ConfigList ?? Enumerable.Empty<ILLMConfig>())
        {
            agent = agent switch
            {
                null => llmConfig switch
                {
                    AzureOpenAIConfig azureConfig => new GPTAgent(this.Name!, this.systemMessage, azureConfig, temperature: config.Temperature ?? 0, functions: config.FunctionDefinitions),
                    OpenAIConfig openAIConfig => new GPTAgent(this.Name!, this.systemMessage, openAIConfig, temperature: config.Temperature ?? 0, functions: config.FunctionDefinitions),
                    _ => throw new ArgumentException($"Unsupported config type {llmConfig.GetType()}"),
                },
                IAgent innerAgent => innerAgent.RegisterReply(async (messages, cancellationToken) =>
                {
                    return await innerAgent.GenerateReplyAsync(messages, cancellationToken: cancellationToken);
                }),
            };
        }

        return agent;
    }

    public string Name { get; }

    public Func<IEnumerable<Message>, CancellationToken, Task<bool>>? IsTermination { get; }

    public async Task<Message> GenerateReplyAsync(
        IEnumerable<Message> messages,
        GenerateReplyOptions? overrideOptions = null,
        CancellationToken cancellationToken = default)
    {
        // if there's no system message, add system message to the first of chat history
        if (!messages.Any(m => m.Role == Role.System))
        {
            var systemMessage = new Message(Role.System, this.systemMessage, from: this.Name);
            messages = new[] { systemMessage }.Concat(messages);
        }

        // process order: function_call -> human_input -> inner_agent -> default_reply -> self_execute
        // first in, last out

        // process default reply
        IAgent agent = new DefaultReplyAgent(this.Name!, this.defaultReply ?? "Default reply is not set. Please pass a default reply to assistant agent");

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

                var msg = await this.innerAgent.GenerateReplyAsync(updatedMessages, overrideOptions, cancellationToken);
                msg.From = this.Name;

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
                var input = await this.GetHumanInputAsync();
                if (input != null)
                {
                    return new Message(Role.Assistant, input, from: this.Name);
                }
                else
                {
                    return new Message(Role.Assistant, string.Empty, from: this.Name);
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
        agent = agent.RegisterMiddleware(async (messages, option, innerAgent, cancellationToken) =>
        {
            if (this.functionMap != null &&
                messages.Last()?.FunctionName is string functionName &&
                messages.Last()?.FunctionArguments is string functionArguments &&
                messages.Last()?.Content is null &&
                this.functionMap.ContainsKey(functionName) &&
                messages.Last().From != this.Name)
            {
                var reply = await this.ExecuteFunctionCallAsync(messages.Last(), cancellationToken);

                // perform as a proxy to run function call from external agent, therefore, the reply should be from the last message's sender
                reply.Role = Role.Function;

                return reply;
            }

            var agentReply = await innerAgent.GenerateReplyAsync(messages, option, cancellationToken);
            if (this.functionMap != null && agentReply.FunctionName is string && agentReply.FunctionArguments is string)
            {
                return await this.ExecuteFunctionCallAsync(agentReply, cancellationToken);
            }
            else
            {
                return agentReply;
            }
        });

        return await agent.GenerateReplyAsync(messages, overrideOptions, cancellationToken);
    }

    private async Task<Message> ExecuteFunctionCallAsync(Message message, CancellationToken _)
    {
        if (message.FunctionName is string functionName && message.FunctionArguments is string functionArguments && this.functionMap != null)
        {
            if (this.functionMap.TryGetValue(functionName, out var func))
            {
                var result = await func(functionArguments);
                return new Message(Role.Assistant, result, from: this.Name)
                {
                    FunctionName = functionName,
                    FunctionArguments = functionArguments,
                };
            }
            else
            {
                var errorMessage = $"Function {functionName} is not available. Available functions are: {string.Join(", ", this.functionMap.Select(f => f.Key))}";
                return new Message(Role.Assistant, errorMessage, from: this.Name)
                {
                    FunctionName = functionName,
                    FunctionArguments = functionArguments,
                };
            }
        }

        throw new Exception("Function call is not available. Please pass a function map to assistant agent");
    }
}
