// Copyright (c) Microsoft Corporation. All rights reserved.
// OpenAIChatCompletionService.cs

using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using AutoGen.Core;
using AutoGen.Service.OpenAI.DTO;

namespace AutoGen.Server;

public class OpenAIChatCompletionService
{
    private readonly IAgent agent;

    public OpenAIChatCompletionService(IAgent agent)
    {
        this.agent = agent;
    }

    public async Task<OpenAIChatCompletion> GetChatCompletionAsync(OpenAIChatCompletionOption request)
    {
        var messages = request.Messages?
            .Select<OpenAIMessage, IMessage>(m => m switch
            {
                OpenAISystemMessage systemMessage when systemMessage.Content is string content => new TextMessage(Role.System, content, this.agent.Name),
                OpenAIUserMessage userMessage when userMessage.Content is string content => new TextMessage(Role.User, content, this.agent.Name),
                OpenAIAssistantMessage assistantMessage when assistantMessage.Content is string content => new TextMessage(Role.Assistant, content, this.agent.Name),
                OpenAIUserMultiModalMessage userMultiModalMessage when userMultiModalMessage.Content is { Length: > 0 } => this.CreateMultiModaMessageFromOpenAIUserMultiModalMessage(userMultiModalMessage),
                _ => throw new ArgumentException($"Unsupported message type {m.GetType()}")
            }) ?? Array.Empty<IMessage>();

        var generateOption = new GenerateReplyOptions()
        {
            Temperature = request.Temperature,
            MaxToken = request.MaxTokens,
        };

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
                FinishReason = "completed",
            };

            openAIChatCompletion.Choices = [choice];

            return openAIChatCompletion;
        }

        throw new NotImplementedException("Unsupported reply content type");
    }

    private MultiModalMessage CreateMultiModaMessageFromOpenAIUserMultiModalMessage(OpenAIUserMultiModalMessage message)
    {
        if (message.Content is null)
        {
            throw new ArgumentNullException(nameof(message.Content));
        }

        IEnumerable<IMessage> items = message.Content.Select<IOpenAIUserMessageItem, IMessage>(item => item switch
        {
            OpenAIUserImageContent imageContent when imageContent.Url is string url => new ImageMessage(Role.User, url, this.agent.Name),
            OpenAIUserTextContent textContent when textContent.Content is string content => new TextMessage(Role.User, content, this.agent.Name),
            _ => throw new ArgumentException($"Unsupported content type {item.GetType()}")
        });

        return new MultiModalMessage(Role.User, items, this.agent.Name);
    }
}
