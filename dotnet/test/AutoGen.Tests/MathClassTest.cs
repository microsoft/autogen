// Copyright (c) Microsoft Corporation. All rights reserved.
// MathClassTest.cs

using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using AutoGen.Extension;
using FluentAssertions;
using Microsoft.SemanticKernel.AI.ChatCompletion;
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

        [FunctionAttribution]
        public async Task<string> CreateMathQuestion(string question, int question_index)
        {
            return $@"// ignore this line [MATH_QUESTION]
Question #{question_index}:
{question}";
        }

        [FunctionAttribution]
        public async Task<string> AnswerQuestion(string answer)
        {
            return $@"// ignore this line [MATH_ANSWER]
{answer}";
        }

        [FunctionAttribution]
        public async Task<string> AnswerIsCorrect(string message)
        {
            return $@"// ignore this line [ANSWER_IS_CORRECT]
{message}";
        }

        [FunctionAttribution]
        public async Task<string> UpdateProgress(int correctAnswerCount)
        {
            if (correctAnswerCount >= 5)
            {
                return GroupChatExtension.TERMINATE;
            }
            else
            {
                return $@"the number of resolved question is {correctAnswerCount}";
            }
        }


        [ApiKeyFact("AZURE_OPENAI_API_KEY")]
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
                temperature: 0,
                functions: new[]
                {
                    this.UpdateProgressFunction,
                },
                functionMap: new Dictionary<string, Func<string, Task<string>>>
                {
                    { this.UpdateProgressFunction.Name, this.UpdateProgressWrapper },
                });

            //var admin = gptAgent
            //    .RegisterReply(async (msgs, ct) =>
            //    {
            //        // check if student successfully resolve 5 math problems
            //        if (msgs.Where(m => m.From == teacher.Name && m.Content?.Contains("[ANSWER_IS_CORRECT]") is true).Count() >= 5)
            //        {
            //            return new Message(AuthorRole.Assistant, GroupChatExtension.TERMINATE, from: "Admin");
            //        }

            //        return null;
            //    });

            await RunMathChatAsync(teacher, student, admin);
        }

        private async Task<IAgent> CreateTeacherAssistantAgentAsync()
        {
            var key = Environment.GetEnvironmentVariable("AZURE_OPENAI_API_KEY") ?? throw new ArgumentException("AZURE_OPENAI_API_KEY is not set");
            var endPoint = Environment.GetEnvironmentVariable("AZURE_OPENAI_ENDPOINT") ?? throw new ArgumentException("AZURE_OPENAI_ENDPOINT is not set");
            var model = "gpt-35-turbo-16k";
            var config = new AzureOpenAIConfig(endPoint, model, key);
            var llmConfig = new AssistantAgentConfig
            {
                ConfigList = new[]
                {
                    config,
                },
                FunctionDefinitions = new[]
                {
                    this.CreateMathQuestionFunction,
                    this.AnswerQuestionFunction,
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
            var llmConfig = new AssistantAgentConfig
            {
                FunctionDefinitions = new[]
                {
                    this.AnswerQuestionFunction,
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

        public async Task RunMathChatAsync(IAgent teacher, IAgent student, IAgent admin)
        {
            var group = new GroupChat(
                admin,
                new[]
                {
                    teacher,
                    student,
                });

            admin.AddInitializeMessage($@"Welcome to the group chat!", group);
            teacher.AddInitializeMessage($@"Hey I'm Teacher", group);
            student.AddInitializeMessage($@"Hey I'm Student", group);
            admin.AddInitializeMessage(@$"Here's the workflow for this group chat:
-group chat workflow-
number_of_resolved_question = 0
while number_of_resolved_question < 5:
    admin_update_number_of_resolved_question
    teacher_create_math_question
    student_answer_question
    teacher_check_answer
    if answer is wrong:
        student_fix_answer
        
admin_terminate_chat
-end-
", group);

            var groupChatManager = new GroupChatManager(group);
            var chatHistory = await admin.SendAsync(groupChatManager, "the number of resolved question is 0", maxRound: 30);

            // print chat history
            foreach (var message in chatHistory)
            {
                _output.WriteLine(message.FormatMessage());
            }

            // check if there's five questions from teacher
            chatHistory.Where(msg => msg.From == teacher.Name && msg.Content?.Contains("[MATH_QUESTION]") is true)
                    .Count()
                    .Should().BeGreaterThanOrEqualTo(5);

            // check if there's more than five answers from student (answer might be wrong)
            chatHistory.Where(msg => msg.From == student.Name && msg.Content?.Contains("[MATH_ANSWER]") is true)
                    .Count()
                    .Should().BeGreaterThanOrEqualTo(5);

            // check if there's five answer_is_correct from teacher
            chatHistory.Where(msg => msg.From == teacher.Name && msg.Content?.Contains("[ANSWER_IS_CORRECT]") is true)
                    .Count()
                    .Should().BeGreaterThanOrEqualTo(5);

            // check if there's terminate chat message from admin
            chatHistory.Where(msg => msg.From == admin.Name && msg.IsGroupChatTerminateMessage())
                    .Count()
                    .Should().Be(1);
        }
    }
}
