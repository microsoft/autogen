// Copyright (c) Microsoft Corporation. All rights reserved.
// AssistantAgent.cs

using System.Collections.Generic;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.SemanticKernel;
using Microsoft.SemanticKernel.AI.ChatCompletion;

namespace AutoGen
{
    public class AssistantAgent : IAgent
    {
        private readonly IKernel kernel;
        private readonly string roleInformation;

        public AssistantAgent(
            string name,
            string roleInformation,
            IKernel kernel)
        {
            this.kernel = kernel;
            this.roleInformation = roleInformation;
            this.Name = name;
        }

        public string Name { get; }

        public async Task<ChatMessage> GenerateReplyAsync(IEnumerable<ChatMessage> messages, CancellationToken? cancellationToken = null)
        {
            var chatMessages = this.ProcessMessages(messages);
            var chatService = this.kernel.GetService<IChatCompletion>() ?? throw new System.Exception("ChatCompletion service is not registered.");

            var chatHistory = chatService.CreateNewChat(roleInformation);
            foreach (var chatMessage in chatMessages)
            {
                chatHistory.Add(chatMessage);
            }

            var response = await chatService.GenerateMessageAsync(chatHistory, cancellationToken: cancellationToken ?? default);

            // todo
            // figure out a way to retrieve functionCall object from chatHistory
            var message = new ChatMessage(AuthorRole.Assistant, response);

            return message;
        }
    }
}
