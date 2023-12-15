// Copyright (c) Microsoft Corporation. All rights reserved.
// GPTAgent.cs

using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.Json;
using System.Text.Json.Serialization;
using System.Threading;
using System.Threading.Tasks;
using Azure.AI.OpenAI;
using Microsoft.SemanticKernel.AI.ChatCompletion;
using Microsoft.SemanticKernel.Connectors.AI.OpenAI.AzureSdk;
using Microsoft.SemanticKernel.Connectors.AI.OpenAI.ChatCompletion;

namespace AutoGen
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
            ChatCompletion = config switch
            {
                AzureOpenAIConfig azureConfig => new AzureOpenAIChatCompletion(azureConfig.DeploymentName, azureConfig.Endpoint, azureConfig.ApiKey, azureConfig.ModelId),
                OpenAIConfig openAIConfig => new OpenAIChatCompletion(openAIConfig.ModelId, openAIConfig.ApiKey),
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

        public IChatCompletion? ChatCompletion { get; }

        public async Task<Message> GenerateReplyAsync(IEnumerable<Message> messages, CancellationToken cancellationToken = default)
        {
            // add system message if there's no system message in messages
            if (!messages.Any(m => m.Role == Role.System))
            {
                messages = new[] { new Message(Role.System, _systemMessage) }.Concat(messages);
            }

            var oaiMessages = this.ProcessMessages(messages);

            var settings = new ChatCompletionsOptions(oaiMessages)
            {
                MaxTokens = _maxTokens,
                Temperature = _temperature,
                Functions = _functions?.ToList() ?? new List<FunctionDefinition>(),
            };

            settings.StopSequences.Add("<meta>");

            var response = await this.openAIClient.GetChatCompletionsAsync(this.modelName, settings, cancellationToken);

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
                    };
                }
                else
                {
                    var errorMessage = $"Function {fc.Name} is not available. Available functions are: {string.Join(", ", this.functionMap.Select(f => f.Key))}";
                    return new Message(Role.Assistant, errorMessage, from: this.Name)
                    {
                        FunctionName = fc.Name,
                        FunctionArguments = fc.Arguments,
                    };
                }
            }
            else
            {
                return new Message(Role.Assistant, oaiMessage.Content)
                {
                    From = this.Name,
                    FunctionName = oaiMessage.FunctionCall?.Name,
                    FunctionArguments = oaiMessage.FunctionCall?.Arguments,
                };
            }
        }

        private OpenAIFunction ToOpenAIFunction(FunctionDefinition functionDefinition)
        {
            var jsonOption = new JsonSerializerOptions
            {
                PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
            };
            var parametersObject = functionDefinition.Parameters.ToObjectFromJson<ParameterObject>(jsonOption);
            var function = new OpenAIFunction
            {
                FunctionName = functionDefinition.Name,
                Description = functionDefinition.Description,
                Parameters = parametersObject.Properties.Select(p => new OpenAIFunctionParameter
                {
                    Name = p.Key,
                    Description = p.Value.Description,
                    IsRequired = parametersObject.Required.Contains(p.Key),
                    Type = p.Value.Type,
                    ParameterType = p.Value.Type switch
                    {
                        "int" => typeof(int),
                        "number" => typeof(double),
                        "string" => typeof(string),
                        "boolean" => typeof(bool),
                        "string[]" => typeof(string[]),
                        "int[]" => typeof(int[]),
                        "number[]" => typeof(double[]),
                        _ => typeof(object),
                    }
                }).ToList(),
            };

            return function;
        }

        private IEnumerable<Azure.AI.OpenAI.ChatMessage> ProcessMessages(IEnumerable<Message> messages)
        {
            var i = 0;
            foreach (var message in messages)
            {
                if (message.Role == Role.System || message.From is null)
                {
                    yield return new Azure.AI.OpenAI.ChatMessage(message.Role.ToString(), message.Content);
                }
                else if (message.From != this.Name)
                {
                    // add as user message
                    var content = message.Content ?? string.Empty;
                    yield return new Azure.AI.OpenAI.ChatMessage(ChatRole.User, content);
                }
                else
                {
                    if (message.FunctionArguments is string functionArguments && message.FunctionName is string functionName)
                    {
                        var chatMessage = new Azure.AI.OpenAI.ChatMessage(ChatRole.Assistant, null)
                        {
                            FunctionCall = new FunctionCall(functionName, functionArguments),
                        };

                        i++;

                        yield return chatMessage;

                        var functionResultMessage = new Azure.AI.OpenAI.ChatMessage(ChatRole.Function, message.Content)
                        {
                            Name = functionName,
                        };

                        yield return functionResultMessage;
                        i++;
                    }
                    else
                    {
                        // add suffix
                        var content = message.Content ?? string.Empty;
                        var chatMessage = new Azure.AI.OpenAI.ChatMessage(ChatRole.Assistant, content);

                        yield return chatMessage;
                    }
                }
            }
        }

        class ParameterObject
        {
            [JsonPropertyName("required")]
            public string[] Required { get; set; } = Array.Empty<string>();

            [JsonPropertyName("properties")]
            public Dictionary<string, OpenAIFunctionParameter> Properties { get; set; } = new Dictionary<string, OpenAIFunctionParameter>();
        }
    }
}
