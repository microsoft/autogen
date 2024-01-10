// Copyright (c) Microsoft Corporation. All rights reserved.
// Example02_TwoAgent_MathChat.cs

using AutoGen;
using FluentAssertions;
using autogen = AutoGen.LLMConfigAPI;

public static class Example02_TwoAgent_MathChat
{
    public static async Task RunAsync()
    {
        // get OpenAI Key and create config
        var openAIKey = Environment.GetEnvironmentVariable("OPENAI_API_KEY") ?? throw new Exception("Please set OPENAI_API_KEY environment variable.");
        var llmConfig = autogen.GetOpenAIConfigList(openAIKey, new[] { "gpt-3.5-turbo" });

        // create teacher agent
        // teacher agent will create math questions
        var teacher = new AssistantAgent(
            name: "teacher",
            systemMessage: @"You are a teacher that create pre-school math question for student and check answer.
If the answer is correct, you terminate conversation by saying [TERMINATE].
If the answer is wrong, you ask student to fix it.",
            llmConfig: new ConversableAgentConfig
            {
                Temperature = 0,
                ConfigList = llmConfig,
            })
            .RegisterPrintFormatMessageHook();

        // create student agent
        // student agent will answer the math questions
        var student = new AssistantAgent(
            name: "student",
            systemMessage: "You are a student that answer question from teacher",
            llmConfig: new ConversableAgentConfig
            {
                Temperature = 0,
                ConfigList = llmConfig,
            })
            .RegisterReply(async (msgs, ct) =>
            {
                // if teacher terminate the conversation, then terminate the conversation by returning [GROUP_CHAT_TERMINATE]
                if (msgs.Last().Content?.Contains("TERMINATE") is true)
                {
                    return new Message(Role.Assistant, GroupChatExtension.TERMINATE)
                    {
                        From = "student",
                    };
                }

                return null;
            })
            .RegisterPrintFormatMessageHook();

        // start the conversation
        var conversation = await student.InitiateChatAsync(
            receiver: teacher,
            message: "Hey teacher, please create math question for me.",
            maxRound: 10);

        // pretty print the conversation
        foreach (var message in conversation)
        {
            Console.WriteLine(message.FormatMessage());
        }

        conversation.Count().Should().BeLessThan(10);
        conversation.Last().IsGroupChatTerminateMessage().Should().BeTrue();
    }
}
