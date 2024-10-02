// Copyright (c) Microsoft Corporation. All rights reserved.
// FunctionExamples.cs

using System.Text.Json;
using AutoGen.Core;

namespace AutoGen.SourceGenerator.Tests
{
    public partial class FunctionExamples
    {
        /// <summary>
        /// Add function
        /// </summary>
        /// <param name="a">a</param>
        /// <param name="b">b</param>
        [FunctionAttribute]
        public int Add(int a, int b)
        {
            return a + b;
        }

        /// <summary>
        /// Add two numbers.
        /// </summary>
        /// <param name="a">The first number.</param>
        /// <param name="b">The second number.</param>
        [Function]
        public Task<string> AddAsync(int a, int b)
        {
            return Task.FromResult($"{a} + {b} = {a + b}");
        }

        /// <summary>
        /// Sum function
        /// </summary>
        /// <param name="args">an array of double values</param>
        [FunctionAttribute]
        public double Sum(double[] args)
        {
            return args.Sum();
        }

        /// <summary>
        /// DictionaryToString function
        /// </summary>
        /// <param name="xargs">an object of key-value pairs. key is string, value is string</param>
        [FunctionAttribute]
        public Task<string> DictionaryToStringAsync(Dictionary<string, string> xargs)
        {
            var res = JsonSerializer.Serialize(xargs, new JsonSerializerOptions
            {
                WriteIndented = true,
            });

            return Task.FromResult(res);
        }

        /// <summary>
        /// query function
        /// </summary>
        /// <param name="query">query, required</param>
        /// <param name="k">top k, optional, default value is 3</param>
        /// <param name="thresold">thresold, optional, default value is 0.5</param>
        [FunctionAttribute]
        public string[] Query(string query, int k = 3, float thresold = 0.5f)
        {
            return Enumerable.Repeat(query, k).ToArray();
        }
    }
}
