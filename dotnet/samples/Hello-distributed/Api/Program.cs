// Copyright (c) Microsoft Corporation. All rights reserved.
// Program.cs

using Api;
using Api.Agents;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AutoGen.Agents;
using Microsoft.AutoGen.Extensions.SemanticKernel;
using Microsoft.AutoGen.Abstractions;

var builder = WebApplication.CreateBuilder(args);

// Add services to the container.
// Learn more about configuring Swagger/OpenAPI at https://aka.ms/aspnetcore/swashbuckle
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen();

builder.AddServiceDefaults();
builder.ConfigureSemanticKernel();

var agentHostUrl = builder.Configuration["AGENT_HOST"]!;
builder.AddAgentWorker(agentHostUrl)
    .AddAgent<HelloAgent>(nameof(HelloAgent))
    .AddAgent<OutputAgent>(nameof(OutputAgent));

builder.Services.AddSingleton<AgentWorker>();

var app = builder.Build();

app.MapDefaultEndpoints();

app.UseSwagger();
app.UseSwaggerUI();

app.MapPost("/sessions", async ([FromBody] string message, Client client) =>
{
    var session = Guid.NewGuid().ToString();
    await client.PublishEventAsync(new NewGreetingRequested { Message = message }.ToCloudEvent(session));
    return session;
});

app.Run();

