// Copyright (c) Microsoft Corporation. All rights reserved.
// Program.cs
using Microsoft.AutoGen.Agents;
using Microsoft.AutoGen.Contracts;
using Microsoft.AutoGen.Core;
using Microsoft.AutoGen.Core.Grpc;

using Samples;

var appBuilder = new AgentsAppBuilder(); // Create app builder
// if we are using distributed, we need the AGENT_HOST var defined and then we will use the grpc runtime
if (Environment.GetEnvironmentVariable("AGENT_HOST") != null)
{
    appBuilder.AddGrpcAgentWorker(
        Environment.GetEnvironmentVariable("AGENT_HOST"))
        .AddAgent<HelloAgent>("HelloAgent");
}
else
{
    // Set up app builder for in-process runtime, allow message delivery to self, and add the Hello agent
    appBuilder.UseInProcessRuntime(deliverToSelf: true).AddAgent<HelloAgent>("HelloAgent");
}
var app = await appBuilder.BuildAsync(); // Build the app
// Create a custom message type from proto and define message
var message = new NewMessageReceived { Message = "Hello World!" };
await app.PublishMessageAsync(message, new TopicId("HelloTopic", "HelloAgents/dotnet")).ConfigureAwait(false); // Publish custom message (handler has been set in HelloAgent)
//await app.PublishMessageAsync(message, new TopicId("HelloTopic")).ConfigureAwait(false); // Publish custom message (handler has been set in HelloAgent)
await app.WaitForShutdownAsync().ConfigureAwait(false); // Wait for shutdown from agent
