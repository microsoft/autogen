// Copyright (c) 2023 - 2024, Owners of https://github.com/autogenhub
// SPDX-License-Identifier: Apache-2.0
// Contributions to this project, i.e., https://github.com/autogenhub/autogen, 
// are licensed under the Apache License, Version 2.0 (Apache-2.0).
// Portions derived from  https://github.com/microsoft/autogen under the MIT License.
// SPDX-License-Identifier: MIT
// Copyright (c) Microsoft Corporation. All rights reserved.
// Program.cs

using System.Runtime.CompilerServices;
using AutoGen.Core;
using AutoGen.WebAPI;

var alice = new DummyAgent("alice");
var bob = new DummyAgent("bob");

var builder = WebApplication.CreateBuilder(args);
// Add services to the container.

// run endpoint at port 5000
builder.WebHost.UseUrls("http://localhost:5000");
var app = builder.Build();

app.UseAgentAsOpenAIChatCompletionEndpoint(alice);
app.UseAgentAsOpenAIChatCompletionEndpoint(bob);

app.Run();

public class DummyAgent : IStreamingAgent
{
    public DummyAgent(string name = "dummy")
    {
        Name = name;
    }

    public string Name { get; }

    public async Task<IMessage> GenerateReplyAsync(IEnumerable<IMessage> messages, GenerateReplyOptions? options = null, CancellationToken cancellationToken = default)
    {
        return new TextMessage(Role.Assistant, $"I am dummy {this.Name}", this.Name);
    }

    public async IAsyncEnumerable<IMessage> GenerateStreamingReplyAsync(IEnumerable<IMessage> messages, GenerateReplyOptions? options = null, [EnumeratorCancellation] CancellationToken cancellationToken = default)
    {
        var reply = $"I am dummy {this.Name}";
        foreach (var c in reply)
        {
            yield return new TextMessageUpdate(Role.Assistant, c.ToString(), this.Name);
        };
    }
}
