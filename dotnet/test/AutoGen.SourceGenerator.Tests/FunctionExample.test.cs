// Copyright (c) Microsoft Corporation. All rights reserved.
// FunctionExample.test.cs

using System.Text.Json;
using ApprovalTests;
using ApprovalTests.Namers;
using ApprovalTests.Reporters;
using AutoGen.OpenAI.Extension;
using FluentAssertions;
using OpenAI.Chat;
using Xunit;

namespace AutoGen.SourceGenerator.Tests
{
    public class FunctionExample
    {
        private readonly FunctionExamples functionExamples = new FunctionExamples();
        private readonly JsonSerializerOptions jsonSerializerOptions = new JsonSerializerOptions
        {
            WriteIndented = true,
        };

        [Fact]
        public void Add_Test()
        {
            var args = new
            {
                a = 1,
                b = 2,
            };

            this.VerifyFunction(functionExamples.AddWrapper, args, 3);
            this.VerifyFunctionDefinition(functionExamples.AddFunctionContract.ToChatTool());
        }

        [Fact]
        public void Sum_Test()
        {
            var args = new
            {
                args = new double[] { 1, 2, 3 },
            };

            this.VerifyFunction(functionExamples.SumWrapper, args, 6.0);
            this.VerifyFunctionDefinition(functionExamples.SumFunctionContract.ToChatTool());
        }

        [Fact]
        public async Task DictionaryToString_Test()
        {
            var args = new
            {
                xargs = new Dictionary<string, string>
                {
                    { "a", "1" },
                    { "b", "2" },
                },
            };

            await this.VerifyAsyncFunction(functionExamples.DictionaryToStringAsyncWrapper, args, JsonSerializer.Serialize(args.xargs, jsonSerializerOptions));
            this.VerifyFunctionDefinition(functionExamples.DictionaryToStringAsyncFunctionContract.ToChatTool());
        }

        [Fact]
        public async Task TopLevelFunctionExampleAddTestAsync()
        {
            var example = new TopLevelStatementFunctionExample();
            var args = new
            {
                a = 1,
                b = 2,
            };

            await this.VerifyAsyncFunction(example.AddWrapper, args, "3");
        }

        [Fact]
        public async Task FilescopeFunctionExampleAddTestAsync()
        {
            var example = new FilescopeNamespaceFunctionExample();
            var args = new
            {
                a = 1,
                b = 2,
            };

            await this.VerifyAsyncFunction(example.AddWrapper, args, "3");
        }

        [Fact]
        public void Query_Test()
        {
            var args = new
            {
                query = "hello",
                k = 3,
            };

            this.VerifyFunction(functionExamples.QueryWrapper, args, new[] { "hello", "hello", "hello" });
            this.VerifyFunctionDefinition(functionExamples.QueryFunctionContract.ToChatTool());
        }

        [UseReporter(typeof(DiffReporter))]
        [UseApprovalSubdirectory("ApprovalTests")]
        private void VerifyFunctionDefinition(ChatTool function)
        {
            var func = new
            {
                name = function.FunctionName,
                description = function.FunctionDescription.Replace(Environment.NewLine, ","),
                parameters = function.FunctionParameters.ToObjectFromJson<object>(options: jsonSerializerOptions),
            };

            Approvals.Verify(JsonSerializer.Serialize(func, jsonSerializerOptions));
        }

        private void VerifyFunction<T, U>(Func<string, T> func, U args, T expected)
        {
            var str = JsonSerializer.Serialize(args, jsonSerializerOptions);
            var res = func(str);
            res.Should().BeEquivalentTo(expected);
        }

        private async Task VerifyAsyncFunction<T, U>(Func<string, Task<T>> func, U args, T expected)
        {
            var str = JsonSerializer.Serialize(args, jsonSerializerOptions);
            var res = await func(str);
            res.Should().BeEquivalentTo(expected);
        }
    }
}
