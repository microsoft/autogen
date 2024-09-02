// Copyright (c) Microsoft Corporation. All rights reserved.
// OpenAIChatCompletionService.cs

using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using AutoGen.Core;
using AutoGen.WebAPI.OpenAI.DTO;
namespace AutoGen.Server;

internal class OpenAIChatCompletionService
{
    private readonly IAgent agent;

    public OpenAIChatCompletionService(IAgent agent)
    {
        this.agent = agent;
    }

    public async Task<OpenAIChatCompletion> GetChatCompletionAsync(OpenAIChatCompletionOption request)
    {
        var messages = this.ProcessMessages(request.Messages ?? Array.Empty<OpenAIMessage>());

        var generateOption = this.ProcessReplyOptions(request);

        var reply = await this.agent.GenerateReplyAsync(messages, generateOption);

        var openAIChatCompletion = new OpenAIChatCompletion()
        {
            Created = DateTimeOffset.UtcNow.Ticks / TimeSpan.TicksPerMillisecond / 1000,
            Model = this.agent.Name,
        };

        if (reply.GetContent() is string content)
        {
            var message = new OpenAIChatCompletionMessage()
            {
                Content = content,
            };

            var choice = new OpenAIChatCompletionChoice()
            {
                Message = message,
                Index = 0,
                FinishReason = "stop",
            };

            openAIChatCompletion.Choices = [choice];

            return openAIChatCompletion;
        }

        throw new NotImplementedException("Unsupported reply content type");
    }

    public async IAsyncEnumerable<OpenAIChatCompletion> GetStreamingChatCompletionAsync(OpenAIChatCompletionOption request)
    {
        if (this.agent is IStreamingAgent streamingAgent)
        {
            var messages = this.ProcessMessages(request.Messages ?? Array.Empty<OpenAIMessage>());

            var generateOption = this.ProcessReplyOptions(request);

            await foreach (var reply in streamingAgent.GenerateStreamingReplyAsync(messages, generateOption))
            {
                var openAIChatCompletion = new OpenAIChatCompletion()
                {
                    Created = DateTimeOffset.UtcNow.Ticks / TimeSpan.TicksPerMillisecond / 1000,
                    Model = this.agent.Name,
                };

                if (reply.GetContent() is string content)
                {
                    var message = new OpenAIChatCompletionMessage()
                    {
                        Content = content,
                    };

                    var choice = new OpenAIChatCompletionChoice()
                    {
                        Delta = message,
                        Index = 0,
                    };

                    openAIChatCompletion.Choices = [choice];

                    yield return openAIChatCompletion;
                }
                else
                {
                    throw new NotImplementedException("Unsupported reply content type");
                }
            }

            var doneMessage = new OpenAIChatCompletion()
            {
                Created = DateTimeOffset.UtcNow.Ticks / TimeSpan.TicksPerMillisecond / 1000,
                Model = this.agent.Name,
            };

            var doneChoice = new OpenAIChatCompletionChoice()
            {
                FinishReason = "stop",
                Index = 0,
            };

            doneMessage.Choices = [doneChoice];

            yield return doneMessage;
        }
        else
        {
            yield return await this.GetChatCompletionAsync(request);
        }
    }

    private IEnumerable<IMessage> ProcessMessages(IEnumerable<OpenAIMessage> messages)
    {
        return messages.Select<OpenAIMessage, IMessage>(m => m switch
        {
            OpenAISystemMessage systemMessage when systemMessage.Content is string content => new TextMessage(Role.System, content, this.agent.Name),
            OpenAIUserMessage userMessage when userMessage.Content is string content => new TextMessage(Role.User, content, this.agent.Name),
            OpenAIAssistantMessage assistantMessage when assistantMessage.Content is string content => new TextMessage(Role.Assistant, content, this.agent.Name),
            OpenAIUserMultiModalMessage userMultiModalMessage when userMultiModalMessage.Content is { Length: > 0 } => this.CreateMultiModaMessageFromOpenAIUserMultiModalMessage(userMultiModalMessage),
            _ => throw new ArgumentException($"Unsupported message type {m.GetType()}")
        });
    }

    private GenerateReplyOptions ProcessReplyOptions(OpenAIChatCompletionOption request)
    {
        return new GenerateReplyOptions()
        {
            Temperature = request.Temperature,
            MaxToken = request.MaxTokens,
            StopSequence = request.Stop,
        };
    }

    private MultiModalMessage CreateMultiModaMessageFromOpenAIUserMultiModalMessage(OpenAIUserMultiModalMessage message)
    {
        if (message.Content is null)
        {
            throw new ArgumentNullException(nameof(message.Content));
        }

        IEnumerable<IMessage> items = message.Content.Select<OpenAIUserMessageItem, IMessage>(item => item switch
        {
            OpenAIUserImageContent imageContent when imageContent.Url is string url => new ImageMessage(Role.User, url, this.agent.Name),
            OpenAIUserTextContent textContent when textContent.Content is string content => new TextMessage(Role.User, content, this.agent.Name),
            _ => throw new ArgumentException($"Unsupported content type {item.GetType()}")
        });

        return new MultiModalMessage(Role.User, items, this.agent.Name);
    }
}
