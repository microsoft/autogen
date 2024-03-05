// Copyright (c) Microsoft Corporation. All rights reserved.
// Program.cs

using AutoGen.BasicSample.CodeSnippet;

var codeSnippet = new PrintMessageMiddlewareCodeSnippet();
// wait user to click enter to continue
Console.ReadLine();
await codeSnippet.PrintMessageStreamingMiddlewareAsync();
