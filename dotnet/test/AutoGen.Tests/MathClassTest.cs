// Copyright (c) Microsoft Corporation. All rights reserved.
// MathClassTest.cs

using System.Linq;
using System.Threading.Tasks;
using AutoGen.Extension;
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


        [ApiKeyFact("AZURE_OPENAI_API_KEY")]
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
            //foreach (var message in chatHistory)
            //{
            //    _output.WriteLine(message.FormatMessage());
            //}

            // check if there's five questions from teacher
            chatHistory.Where(msg => msg.GetFrom() == teacher.Name && msg.Content?.Contains("[MATH_QUESTION]") is true)
                    .Count()
                    .Should().Be(5);

            // check if there's more than five answers from student (answer might be wrong)
            chatHistory.Where(msg => msg.GetFrom() == student.Name && msg.Content?.Contains("[MATH_ANSWER]") is true)
                    .Count()
                    .Should().BeGreaterThanOrEqualTo(5);

            // check if there's five answer_is_correct from teacher
            chatHistory.Where(msg => msg.GetFrom() == teacher.Name && msg.Content?.Contains("[ANSWER_IS_CORRECT]") is true)
                    .Count()
                    .Should().Be(5);

            // check if there's terminate chat message from admin
            chatHistory.Where(msg => msg.GetFrom() == admin.Name && msg.IsGroupChatTerminateMessage())
                    .Count()
                    .Should().Be(1);
        }
    }
}
