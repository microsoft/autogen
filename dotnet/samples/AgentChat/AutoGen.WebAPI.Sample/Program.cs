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
        }
    }
}
