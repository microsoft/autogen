// Copyright (c) Microsoft Corporation. All rights reserved.
// Program.cs

using Backend;
using Backend.Agents;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AutoGen.Abstractions;
using Microsoft.AutoGen.Agents;
using Microsoft.AutoGen.Extensions.SemanticKernel;

var builder = WebApplication.CreateBuilder(args);

builder.AddServiceDefaults();
builder.ConfigureSemanticKernel();

builder.Services.AddHttpClient();
builder.Services.AddControllers();
builder.Services.AddSwaggerGen();

var agentHostUrl = builder.Configuration["AGENT_HOST"]!;
builder.AddAgentWorker(agentHostUrl)
    .AddAgent<HelloAgent>(nameof(HelloAgent))
    .AddAgent<OutputAgent>(nameof(OutputAgent));

builder.Services.AddSingleton<AgentWorker>();

var app = builder.Build();

app.MapDefaultEndpoints();

app.MapPost("/sessions", async ([FromBody]string message, Client client) =>
{
    var session = Guid.NewGuid().ToString();
    await client.PublishEventAsync(new NewGreetingRequested { Message = message }.ToCloudEvent(session));
    return session;
});

app.MapGet("/sessions/{session}", async (string session) =>
{
   
    return session;
});

app.UseRouting()
.UseEndpoints(endpoints =>
{
   
}); ;

app.UseSwagger();
app.UseSwaggerUI(c =>
{
    c.SwaggerEndpoint("/swagger/v1/swagger.json", "My API V1");
});

app.Run();
