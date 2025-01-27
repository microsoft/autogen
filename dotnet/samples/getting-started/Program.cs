// Copyright (c) Microsoft Corporation. All rights reserved.
// Program.cs

using TerminationF = System.Func<int, bool>;
using ModifyF = System.Func<int, int>;
using Microsoft.AutoGen.Core;
using Microsoft.Extensions.Hosting;
using Samples;
using Microsoft.Extensions.DependencyInjection.Extensions;
using Microsoft.AutoGen.Contracts;

ModifyF modifyFunc = (int x) => x - 1;
TerminationF runUntilFunc = (int x) =>
{
    return x <= 1;
};

HostApplicationBuilder builder = new HostApplicationBuilder();
builder.Services.TryAddSingleton(modifyFunc);
builder.Services.TryAddSingleton(runUntilFunc);

AgentsAppBuilder agentApp = new(builder);
agentApp.AddAgent<Checker>("Checker");
agentApp.AddAgent<Modifier>("Modifier");
var app = await agentApp.BuildAsync();

// Send the initial count to the agents app, running on the `local` runtime, and pass through the registered services via the application `builder`
await app.PublishMessageAsync(new CountMessage
{
    Content = 10
}, new TopicId("default"));

// Run until application shutdown
await app.WaitForShutdownAsync();