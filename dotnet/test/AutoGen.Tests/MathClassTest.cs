// Copyright (c) Microsoft Corporation. All rights reserved.
// MathClassTest.cs

using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using AutoGen.OpenAI;
using FluentAssertions;
using Xunit.Abstractions;

namespace AutoGen.Tests
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
            return $@"// ignore this line [MATH_QUESTION]
Question #{question_index}:
{question}";
        }

        [FunctionAttribute]
        public async Task<string> AnswerQuestion(string answer)
        {
            return $@"// ignore this line [MATH_ANSWER]
The answer is {answer}, teacher please check answer";
        }

        [FunctionAttribute]
        public async Task<string> AnswerIsCorrect(string message)
        {
            return $@"// ignore this line [ANSWER_IS_CORRECT]
{message}";
        }

        [FunctionAttribute]
        public async Task<string> UpdateProgress(int correctAnswerCount)
        {
            if (correctAnswerCount >= 5)
            {
                return $@"// ignore this line [UPDATE_PROGRESS]
{GroupChatExtension.TERMINATE}";
            }
            else
            {
                return $@"// ignore this line [UPDATE_PROGRESS]
the number of resolved question is {correctAnswerCount}
teacher, please create the next math question";
            }
        }


        [ApiKeyFact("AZURE_OPENAI_API_KEY", "AZURE_OPENAI_ENDPOINT")]
        public async Task AssistantAgentMathChatTestAsync()
        {
            var teacher = await CreateTeacherAssistantAgentAsync();
            var student = await CreateStudentAssistantAgentAsync();
            var key = Environment.GetEnvironmentVariable("AZURE_OPENAI_API_KEY") ?? throw new ArgumentException("AZURE_OPENAI_API_KEY is not set");
            var endPoint = Environment.GetEnvironmentVariable("AZURE_OPENAI_ENDPOINT") ?? throw new ArgumentException("AZURE_OPENAI_ENDPOINT is not set");
            var model = "gpt-35-turbo-16k";
            var admin = new GPTAgent(
                name: "Admin",
                systemMessage: $@"You are admin. You ask teacher to create 5 math questions. You update progress after each question is answered.",
                config: new AzureOpenAIConfig(endPoint, model, key),
                functions: new[]
                {
                    this.UpdateProgressFunction,
                },
                functionMap: new Dictionary<string, Func<string, Task<string>>>
                {
                    { this.UpdateProgressFunction.Name, this.UpdateProgressWrapper },
                })
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

            await RunMathChatAsync(teacher, student, admin);
        }

        private async Task<IAgent> CreateTeacherAssistantAgentAsync()
        {
            var key = Environment.GetEnvironmentVariable("AZURE_OPENAI_API_KEY") ?? throw new ArgumentException("AZURE_OPENAI_API_KEY is not set");
            var endPoint = Environment.GetEnvironmentVariable("AZURE_OPENAI_ENDPOINT") ?? throw new ArgumentException("AZURE_OPENAI_ENDPOINT is not set");
            var model = "gpt-35-turbo-16k";
            var config = new AzureOpenAIConfig(endPoint, model, key);
            var llmConfig = new ConversableAgentConfig
            {
                ConfigList = new[]
                {
                    config,
                },
                FunctionContracts = new[]
                {
                    this.CreateMathQuestionFunctionContract,
                    this.AnswerIsCorrectFunctionContract,
                },
            };

            var teacher = new AssistantAgent(
                            name: "Teacher",
                            systemMessage: $@"You are a preschool math teacher.
You create math question and ask student to answer it.
Then you check if the answer is correct.
If the answer is wrong, you ask student to fix it.
If the answer is correct, you create another math question.
",
                            llmConfig: llmConfig,
                            functionMap: new Dictionary<string, Func<string, Task<string>>>
                            {
                                { this.CreateMathQuestionFunction.Name, this.CreateMathQuestionWrapper },
                                { this.AnswerIsCorrectFunction.Name, this.AnswerIsCorrectWrapper },
                            });

            return teacher;
        }

        private async Task<IAgent> CreateStudentAssistantAgentAsync()
        {
            var key = Environment.GetEnvironmentVariable("AZURE_OPENAI_API_KEY") ?? throw new ArgumentException("AZURE_OPENAI_API_KEY is not set");
            var endPoint = Environment.GetEnvironmentVariable("AZURE_OPENAI_ENDPOINT") ?? throw new ArgumentException("AZURE_OPENAI_ENDPOINT is not set");
            var model = "gpt-35-turbo-16k";
            var config = new AzureOpenAIConfig(endPoint, model, key);
            var llmConfig = new ConversableAgentConfig
            {
                FunctionContracts = new[]
                {
                    this.AnswerQuestionFunctionContract,
                },
                ConfigList = new[]
                {
                    config,
                },
            };
            var student = new AssistantAgent(
                            name: "Student",
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
",
                            llmConfig: llmConfig,
                            functionMap: new Dictionary<string, Func<string, Task<string>>>
                            {
                                { this.AnswerQuestionFunction.Name, this.AnswerQuestionWrapper }
                            });

            return student;
        }

        private async Task RunMathChatAsync(IAgent teacher, IAgent student, IAgent admin)
        {
            var group = new GroupChat(
                [
                    admin,
                    teacher,
                    student,
                ],
                admin);

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
