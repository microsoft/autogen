// Copyright (c) Microsoft Corporation. All rights reserved.
// MathClassTest.cs

using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using AutoGen.OpenAI.Extension;
using AutoGen.Tests;
using Azure.AI.OpenAI;
using FluentAssertions;
using Xunit.Abstractions;

namespace AutoGen.OpenAI.Tests
{
    public partial class MathClassTest
    {
        private readonly ITestOutputHelper _output;
        public MathClassTest(ITestOutputHelper output)
        {
            _output = output;
        }

        [FunctionAttribute]
        public async Task<string> CreateMathQuestion(string question, int question_index)
        {
            return $@"[MATH_QUESTION]
Question #{question_index}:
{question}";
        }

        [FunctionAttribute]
        public async Task<string> AnswerQuestion(string answer)
        {
            return $@"[MATH_ANSWER]
The answer is {answer}, teacher please check answer";
        }

        [FunctionAttribute]
        public async Task<string> AnswerIsCorrect(string message)
        {
            return $@"[ANSWER_IS_CORRECT]
{message}";
        }

        [FunctionAttribute]
        public async Task<string> UpdateProgress(int correctAnswerCount)
        {
            if (correctAnswerCount >= 5)
            {
                return $@"[UPDATE_PROGRESS]
{GroupChatExtension.TERMINATE}";
            }
            else
            {
                return $@"[UPDATE_PROGRESS]
the number of resolved question is {correctAnswerCount}
teacher, please create the next math question";
            }
        }


        [ApiKeyFact("AZURE_OPENAI_API_KEY", "AZURE_OPENAI_ENDPOINT")]
        public async Task OpenAIAgentMathChatTestAsync()
        {
            var key = Environment.GetEnvironmentVariable("AZURE_OPENAI_API_KEY") ?? throw new ArgumentException("AZURE_OPENAI_API_KEY is not set");
            var endPoint = Environment.GetEnvironmentVariable("AZURE_OPENAI_ENDPOINT") ?? throw new ArgumentException("AZURE_OPENAI_ENDPOINT is not set");

            var openaiClient = new OpenAIClient(new Uri(endPoint), new Azure.AzureKeyCredential(key));
            var model = "gpt-35-turbo-16k";
            var teacher = await CreateTeacherAgentAsync(openaiClient, model);
            var student = await CreateStudentAssistantAgentAsync(openaiClient, model);

            var adminFunctionMiddleware = new FunctionCallMiddleware(
                functions: [this.UpdateProgressFunctionContract],
                functionMap: new Dictionary<string, Func<string, Task<string>>>
                {
                    { this.UpdateProgressFunction.Name!, this.UpdateProgressWrapper },
                });
            var admin = new OpenAIChatAgent(
                openAIClient: openaiClient,
                modelName: model,
                name: "Admin",
                systemMessage: $@"You are admin. You ask teacher to create 5 math questions. You update progress after each question is answered.")
                .RegisterMessageConnector()
                .RegisterStreamingMiddleware(adminFunctionMiddleware)
                .RegisterMiddleware(async (messages, options, agent, ct) =>
                {
                    // check admin reply to make sure it calls UpdateProgress function
                    var maxAttempt = 5;
                    var reply = await agent.GenerateReplyAsync(messages, options, ct);
                    while (maxAttempt-- > 0)
                    {
                        if (options?.Functions is { Length: 0 })
                        {
                            return reply;
                        }

                        var formattedMessage = reply.FormatMessage();
                        this._output.WriteLine(formattedMessage);
                        if (reply.GetContent()?.Contains("[UPDATE_PROGRESS]") is true)
                        {
                            return reply;
                        }
                        else
                        {
                            await Task.Delay(1000);
                            var review = "Admin, please update progress based on conversation";
                            reply = await agent.SendAsync(review, messages, ct);
                        }
                    }

                    throw new Exception("Admin does not call UpdateProgress function");
                });

            var groupAdmin = new OpenAIChatAgent(
                openAIClient: openaiClient,
                modelName: model,
                name: "GroupAdmin",
                systemMessage: "You are group admin. You manage the group chat.")
                .RegisterMessageConnector();
            await RunMathChatAsync(teacher, student, admin, groupAdmin);
        }

        private async Task<IAgent> CreateTeacherAgentAsync(OpenAIClient client, string model)
        {
            var functionCallMiddleware = new FunctionCallMiddleware(
                functions: [this.CreateMathQuestionFunctionContract, this.AnswerIsCorrectFunctionContract],
                functionMap: new Dictionary<string, Func<string, Task<string>>>
                {
                    { this.CreateMathQuestionFunctionContract.Name!, this.CreateMathQuestionWrapper },
                    { this.AnswerIsCorrectFunctionContract.Name!, this.AnswerIsCorrectWrapper },
                });

            var teacher = new OpenAIChatAgent(
                openAIClient: client,
                name: "Teacher",
                systemMessage: $@"You are a preschool math teacher.
You create math question and ask student to answer it.
Then you check if the answer is correct.
If the answer is wrong, you ask student to fix it.
If the answer is correct, you create another math question.",
                modelName: model)
                .RegisterMessageConnector()
                .RegisterStreamingMiddleware(functionCallMiddleware);

            return teacher;
        }

        private async Task<IAgent> CreateStudentAssistantAgentAsync(OpenAIClient client, string model)
        {
            var functionCallMiddleware = new FunctionCallMiddleware(
                functions: [this.AnswerQuestionFunctionContract],
                functionMap: new Dictionary<string, Func<string, Task<string>>>
                {
                    { this.AnswerQuestionFunctionContract.Name!, this.AnswerQuestionWrapper },
                });
            var student = new OpenAIChatAgent(
                openAIClient: client,
                name: "Student",
                modelName: model,
                systemMessage: $@"You are a student. Here's your workflow in pseudo code:
-workflow-
answer_question
if answer is wrong
    fix_answer
-end-

Here are a few examples of answer_question:
-example 1-
2

Here are a few examples of fix_answer:
-example 1-
sorry, the answer should be 2, not 3
")
                .RegisterMessageConnector()
                .RegisterStreamingMiddleware(functionCallMiddleware);

            return student;
        }

        private async Task RunMathChatAsync(IAgent teacher, IAgent student, IAgent admin, IAgent groupAdmin)
        {
            var group = new GroupChat(
                [
                    admin,
                    teacher,
                    student,
                ],
                groupAdmin);

            admin.SendIntroduction($@"Welcome to the group chat! I'm admin", group);
            teacher.SendIntroduction($@"Hey I'm Teacher", group);
            student.SendIntroduction($@"Hey I'm Student", group);
            admin.SendIntroduction(@$"Teacher, please create pre-school math question for student and check answer.
Student, for each question, please answer it and ask teacher to check if the answer is correct.
I'll update the progress after each question is answered.
The conversation will end after 5 correct answers.
", group);

            var groupChatManager = new GroupChatManager(group);
            var chatHistory = await admin.InitiateChatAsync(groupChatManager, maxRound: 50);

            // print chat history
            foreach (var message in chatHistory)
            {
                _output.WriteLine(message.FormatMessage());
            }

            // check if there's five questions from teacher
            chatHistory.Where(msg => msg.From == teacher.Name && msg.GetContent()?.Contains("[MATH_QUESTION]") is true)
                    .Count()
                    .Should().BeGreaterThanOrEqualTo(5);

            // check if there's more than five answers from student (answer might be wrong)
            chatHistory.Where(msg => msg.From == student.Name && msg.GetContent()?.Contains("[MATH_ANSWER]") is true)
                    .Count()
                    .Should().BeGreaterThanOrEqualTo(5);

            // check if there's five answer_is_correct from teacher
            chatHistory.Where(msg => msg.From == teacher.Name && msg.GetContent()?.Contains("[ANSWER_IS_CORRECT]") is true)
                    .Count()
                    .Should().BeGreaterThanOrEqualTo(5);

            // check if there's terminate chat message from admin
            chatHistory.Where(msg => msg.From == admin.Name && msg.IsGroupChatTerminateMessage())
                    .Count()
                    .Should().Be(1);
        }
    }
}
