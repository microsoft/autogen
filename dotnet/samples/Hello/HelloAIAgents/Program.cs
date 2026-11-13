// Copyright (c) Microsoft Corporation. All rights reserved.
// Program.cs

using Hello;
using Microsoft.AutoGen.Agents;
using Microsoft.AutoGen.Contracts;
using Microsoft.AutoGen.Core;
using Microsoft.AutoGen.Core.Grpc;

const string serviceName = "HelloAIAgents";
var connectionString = Environment.GetEnvironmentVariable("AZURE_OPENAI_CONNECTION_STRING")
    ?? throw new InvalidOperationException(
        "AZURE_OPENAI_CONNECTION_STRING is not set. Expected: "
        + "Endpoint=https://<resource>.openai.azure.com/;Key=<key>;Deployment=<deployment>");

var hostBuilder = new HostApplicationBuilder();
hostBuilder.Configuration[$"ConnectionStrings:{serviceName}"] = connectionString;
hostBuilder.AddOpenAIChatClient(serviceName);

var appBuilder = new AgentsAppBuilder(hostBuilder);
var hostAddress = Environment.GetEnvironmentVariable("AGENT_HOST");
if (hostAddress is not null)
{
    appBuilder.AddGrpcAgentWorker(hostAddress)
        .AddAgent<HelloAIAgent>("HelloAIAgent");
}
else
{
    appBuilder.UseInProcessRuntime()
        .AddAgent<HelloAIAgent>("HelloAIAgent");
}

var app = await appBuilder.BuildAsync();
await app.StartAsync();
await app.PublishMessageAsync(
    new NewMessageReceived { Message = "World" },
    new TopicId("HelloAITopic"));
await app.WaitForShutdownAsync();
