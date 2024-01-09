// Copyright (c) Microsoft Corporation. All rights reserved.
// GPTAgent.cs

using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using Azure.AI.OpenAI;

namespace AutoGen.OpenAI
{
    public class GPTAgent : IAgent
    {
        private readonly string _systemMessage;
        private readonly IEnumerable<FunctionDefinition>? _functions;
        private readonly float _temperature;
        private readonly int _maxTokens = 1024;
        private readonly IDictionary<string, Func<string, Task<string>>>? functionMap;
        private readonly OpenAIClient openAIClient;
        private readonly string? modelName;

        public GPTAgent(
            string name,
            string systemMessage,
            ILLMConfig config,
            float temperature = 0.7f,
            int maxTokens = 1024,
            IEnumerable<FunctionDefinition>? functions = null,
            IDictionary<string, Func<string, Task<string>>>? functionMap = null)
        {
            ChatLLM = config switch
            {
                AzureOpenAIConfig azureConfig => OpenAIChatLLM.Create(azureConfig),
                OpenAIConfig openAIConfig => OpenAIChatLLM.Create(openAIConfig),
                _ => throw new ArgumentException($"Unsupported config type {config.GetType()}"),
            };

            openAIClient = config switch
            {
                AzureOpenAIConfig azureConfig => new OpenAIClient(new Uri(azureConfig.Endpoint), new Azure.AzureKeyCredential(azureConfig.ApiKey)),
                OpenAIConfig openAIConfig => new OpenAIClient(openAIConfig.ApiKey),
                _ => throw new ArgumentException($"Unsupported config type {config.GetType()}"),
            };

            modelName = config switch
            {
                AzureOpenAIConfig azureConfig => azureConfig.DeploymentName,
                OpenAIConfig openAIConfig => openAIConfig.ModelId,
                _ => throw new ArgumentException($"Unsupported config type {config.GetType()}"),
            };

            _systemMessage = systemMessage;
            _functions = functions;
            Name = name;
            _temperature = temperature;
            _maxTokens = maxTokens;
            this.functionMap = functionMap;
        }

        public string? Name { get; }

        public IChatLLM? ChatLLM { get; }

        public async Task<Message> GenerateReplyAsync(IEnumerable<Message> messages, CancellationToken cancellationToken = default)
        {
            // add system message if there's no system message in messages
            if (!messages.Any(m => m.Role == Role.System))
            {
                messages = new[] { new Message(Role.System, _systemMessage) }.Concat(messages);
            }

            var oaiMessages = this.ProcessMessages(messages);

            var settings = new ChatCompletionsOptions(this.modelName, oaiMessages)
            {
                MaxTokens = _maxTokens,
                Temperature = _temperature,
            };

            if (_functions != null)
            {
                settings.Functions = _functions.ToList();
            }

            //settings.StopSequences.Add("<meta>");

            var response = await this.openAIClient.GetChatCompletionsAsync(settings, cancellationToken);

            var oaiMessage = response.Value.Choices.First().Message;

            if (this.functionMap != null && oaiMessage.FunctionCall is FunctionCall fc)
            {
                if (this.functionMap.TryGetValue(fc.Name, out var func))
                {
                    var result = await func(fc.Arguments);
                    return new Message(Role.Assistant, result, from: this.Name)
                    {
                        FunctionName = fc.Name,
                        FunctionArguments = fc.Arguments,
                        Value = oaiMessage,
                    };
                }
                else
                {
                    var errorMessage = $"Function {fc.Name} is not available. Available functions are: {string.Join(", ", this.functionMap.Select(f => f.Key))}";
                    return new Message(Role.Assistant, errorMessage, from: this.Name)
                    {
                        FunctionName = fc.Name,
                        FunctionArguments = fc.Arguments,
                        Value = oaiMessage,
                    };
                }
            }
            else
            {
                if (string.IsNullOrEmpty(oaiMessage.Content) && oaiMessage.FunctionCall is null)
                {
                    throw new Exception("OpenAI response is invalid.");
                }
                return new Message(Role.Assistant, oaiMessage.Content)
                {
                    From = this.Name,
                    FunctionName = oaiMessage.FunctionCall?.Name,
                    FunctionArguments = oaiMessage.FunctionCall?.Arguments,
                    Value = oaiMessage,
                };
            }
        }

        private IEnumerable<ChatRequestMessage> ProcessMessages(IEnumerable<Message> messages)
        {
            var i = 0;
            foreach (var message in messages)
            {
                if (message.Role == Role.System || message.From is null)
                {
                    if (message.Role == Role.System)
                    {
                        // add as system message
                        yield return message.ToChatRequestSystemMessage();
                    }
                    else
                    {
                        // add as user message
                        yield return message.ToChatRequestUserMessage();
                    }
                }
                else if (message.From != this.Name)
                {
                    // add as user message
                    yield return message.ToChatRequestUserMessage();
                }
                else
                {
                    if (message.FunctionArguments is string functionArguments && message.FunctionName is string functionName)
                    {
                        var chatMessage = new ChatRequestAssistantMessage(string.Empty)
                        {
                            FunctionCall = new FunctionCall(functionName, functionArguments),
                        };

                        i++;

                        yield return message.ToChatRequestAssistantMessage();

                        var functionResultMessage = new ChatRequestFunctionMessage(functionName, message.Content);

                        yield return message.ToChatRequestFunctionMessage();
                        i++;
                    }
                    else
                    {
                        yield return message.ToChatRequestAssistantMessage();
                    }
                }
            }
        }
    }
}
