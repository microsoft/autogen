// Copyright (c) Microsoft Corporation. All rights reserved.
// GPTAgent.cs

using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.Json;
using System.Text.Json.Serialization;
using System.Threading;
using System.Threading.Tasks;
using AutoGen.Extension;
using Azure.AI.OpenAI;
using Microsoft.SemanticKernel.AI.ChatCompletion;
using Microsoft.SemanticKernel.Connectors.AI.OpenAI;
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

        public GPTAgent(
            string name,
            string systemMessage,
            ILLMConfig config,
            float temperature = 0f,
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
            // if there's no system message in messages, add one
            ChatHistory? chatHistory = null;
            if (messages.Any(m => m.Role == AuthorRole.System))
            {
                chatHistory = ChatCompletion!.CreateNewChat();
            }
            else
            {
                chatHistory = ChatCompletion!.CreateNewChat(_systemMessage);
            }

            messages = this.ProcessMessages(messages);
            foreach (var msg in messages)
            {
                chatHistory.Add(msg);
            }

            var setting = new OpenAIRequestSettings
            {
                Temperature = _temperature,
                StopSequences = new[] { "<eof_msg>" },
                Functions = _functions?.Select(f => this.ToOpenAIFunction(f)).ToList(),
                MaxTokens = _maxTokens,
                FunctionCall = OpenAIRequestSettings.FunctionCallAuto,
            };

            var response = await this.ChatCompletion!.GetChatCompletionsAsync(chatHistory, setting, cancellationToken);

            if (response.Count() > 1)
            {
                throw new Exception("Multiple responses are not supported.");
            }

            var res = await response.First().GetChatMessageAsync();
            Message message;
            if (res is AzureOpenAIChatMessage aoaiMessage && aoaiMessage.InnerChatMessage is Azure.AI.OpenAI.ChatMessage oaiMessage)
            {
                message = new Message(AuthorRole.Assistant, oaiMessage.Content, from: this.Name)
                {
                    FunctionCall = oaiMessage.FunctionCall,
                };
            }
            else
            {
                message = new Message(AuthorRole.Assistant, res.Content, from: this.Name)
                {
                    FunctionCall = res.GetFunctionCall(),
                };
            }

            if (this.functionMap != null && message.FunctionCall is FunctionCall fc)
            {
                if (this.functionMap.TryGetValue(fc.Name, out var func))
                {
                    var result = await func(fc.Arguments);
                    return new Message(AuthorRole.Assistant, result, from: this.Name)
                    {
                        FunctionCall = fc,
                    };
                }
                else
                {
                    var errorMessage = $"Function {fc.Name} is not available. Available functions are: {string.Join(", ", this.functionMap.Select(f => f.Key))}";
                    return new Message(AuthorRole.Assistant, errorMessage, from: this.Name)
                    {
                        FunctionCall = fc,
                    };
                }
            }
            else
            {
                return message;
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

        class ParameterObject
        {
            [JsonPropertyName("required")]
            public string[] Required { get; set; } = Array.Empty<string>();

            [JsonPropertyName("properties")]
            public Dictionary<string, OpenAIFunctionParameter> Properties { get; set; } = new Dictionary<string, OpenAIFunctionParameter>();
        }
    }
}
