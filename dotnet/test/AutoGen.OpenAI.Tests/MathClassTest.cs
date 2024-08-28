// Copyright (c) Microsoft Corporation. All rights reserved.
// MathClassTest.cs

using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using AutoGen.OpenAI.Extension;
using AutoGen.Tests;
using Azure.AI.OpenAI;
using FluentAssertions;
using OpenAI;
using Xunit.Abstractions;

namespace AutoGen.OpenAI.Tests
{
    public partial class MathClassTest
    {
        private readonly ITestOutputHelper _output;

        // as of 2024-05-20, aoai return 500 error when round > 1
        // I'm pretty sure that round > 5 was supported before
        // So this is probably some wield regression on aoai side
        // I'll keep this test case here for now, plus setting round to 1
        // so the test can still pass.
        // In the future, we should rewind this test case to round > 1 (previously was 5)
        private int round = 1;
        public MathClassTest(ITestOutputHelper output)
        {
            _output = output;
        }

        private Task<IMessage> Print(IEnumerable<IMessage> messages, GenerateReplyOptions? option, IAgent agent, CancellationToken ct)
        {
            try
            {
                var reply = agent.GenerateReplyAsync(messages, option, ct).Result;

                _output.WriteLine(reply.FormatMessage());
                return Task.FromResult(reply);
            }
            catch (Exception)
            {
                _output.WriteLine("Request failed");
                _output.WriteLine($"agent name: {agent.Name}");
                foreach (var message in messages)
                {
                    _output.WriteLine(message.FormatMessage());
                }

                throw;
            }

        }

        [FunctionAttribute]
        public async Task<string> CreateMathQuestion(string question, int question_index)
        {
            return $@"[MATH_QUESTION]
Question {question_index}:
{question}

Student, please answer";
        }

        [FunctionAttribute]
        public async Task<string> AnswerQuestion(string answer)
        {
            return $@"[MATH_ANSWER]
The answer is {answer}
teacher please check answer";
        }

        [FunctionAttribute]
        public async Task<string> AnswerIsCorrect(string message)
        {
            return $@"[ANSWER_IS_CORRECT]
{message}
please update progress";
        }

        [FunctionAttribute]
        public async Task<string> UpdateProgress(int correctAnswerCount)
        {
            if (correctAnswerCount >= this.round)
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


        [ApiKeyFact("AZURE_OPENAI_API_KEY", "AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_DEPLOY_NAME")]
        public async Task OpenAIAgentMathChatTestAsync()
        {
            var key = Environment.GetEnvironmentVariable("AZURE_OPENAI_API_KEY") ?? throw new ArgumentException("AZURE_OPENAI_API_KEY is not set");
            var endPoint = Environment.GetEnvironmentVariable("AZURE_OPENAI_ENDPOINT") ?? throw new ArgumentException("AZURE_OPENAI_ENDPOINT is not set");
            var deployName = Environment.GetEnvironmentVariable("AZURE_OPENAI_DEPLOY_NAME") ?? throw new ArgumentException("AZURE_OPENAI_DEPLOY_NAME is not set");
            var openaiClient = new AzureOpenAIClient(new Uri(endPoint), new Azure.AzureKeyCredential(key));
            var teacher = await CreateTeacherAgentAsync(openaiClient, deployName);
            var student = await CreateStudentAssistantAgentAsync(openaiClient, deployName);

            var adminFunctionMiddleware = new FunctionCallMiddleware(
                functions: [this.UpdateProgressFunctionContract],
                functionMap: new Dictionary<string, Func<string, Task<string>>>
                {
                    { this.UpdateProgressFunctionContract.Name, this.UpdateProgressWrapper },
                });
            var admin = new OpenAIChatAgent(
                chatClient: openaiClient.GetChatClient(deployName),
                name: "Admin",
                systemMessage: $@"You are admin. You update progress after each question is answered.")
                .RegisterMessageConnector()
                .RegisterStreamingMiddleware(adminFunctionMiddleware)
                .RegisterMiddleware(Print);

            var groupAdmin = new OpenAIChatAgent(
                chatClient: openaiClient.GetChatClient(deployName),
                name: "GroupAdmin",
                systemMessage: "You are group admin. You manage the group chat.")
                .RegisterMessageConnector()
                .RegisterMiddleware(Print);
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
                chatClient: client.GetChatClient(model),
                name: "Teacher",
                systemMessage: @"You are a preschool math teacher.
You create math question and ask student to answer it.
Then you check if the answer is correct.
If the answer is wrong, you ask student to fix it")
                .RegisterMessageConnector()
                .RegisterStreamingMiddleware(functionCallMiddleware)
                .RegisterMiddleware(Print);

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
                chatClient: client.GetChatClient(model),
                name: "Student",
                systemMessage: @"You are a student. You answer math question from teacher.")
                .RegisterMessageConnector()
                .RegisterStreamingMiddleware(functionCallMiddleware)
                .RegisterMiddleware(Print);

            return student;
        }

        private async Task RunMathChatAsync(IAgent teacher, IAgent student, IAgent admin, IAgent groupAdmin)
        {
            var teacher2Student = Transition.Create(teacher, student);
            var student2Teacher = Transition.Create(student, teacher);
            var teacher2Admin = Transition.Create(teacher, admin);
            var admin2Teacher = Transition.Create(admin, teacher);
            var workflow = new Graph(
                [
                    teacher2Student,
                    student2Teacher,
                    teacher2Admin,
                    admin2Teacher,
                ]);
            var group = new GroupChat(
                workflow: workflow,
                members: [
                    admin,
                    teacher,
                    student,
                ],
                admin: groupAdmin);

            var groupChatManager = new GroupChatManager(group);
            var chatHistory = await admin.InitiateChatAsync(groupChatManager, "teacher, create question", maxRound: 50);

            chatHistory.Where(msg => msg.From == teacher.Name && msg.GetContent()?.Contains("[MATH_QUESTION]") is true)
                    .Count()
                    .Should().BeGreaterThanOrEqualTo(this.round);

            chatHistory.Where(msg => msg.From == student.Name && msg.GetContent()?.Contains("[MATH_ANSWER]") is true)
                    .Count()
                    .Should().BeGreaterThanOrEqualTo(this.round);

            chatHistory.Where(msg => msg.From == teacher.Name && msg.GetContent()?.Contains("[ANSWER_IS_CORRECT]") is true)
                    .Count()
                    .Should().BeGreaterThanOrEqualTo(this.round);

            // check if there's terminate chat message from admin
            chatHistory.Where(msg => msg.From == admin.Name && msg.IsGroupChatTerminateMessage())
                    .Count()
                    .Should().Be(1);
        }
    }
}
