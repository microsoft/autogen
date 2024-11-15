// Copyright (c) Microsoft Corporation. All rights reserved.
// Program.cs

using Backend.Agents;
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
    .AddAgent<HelloAgent>(nameof(HelloAgent));

builder.Services.AddSingleton<AgentWorker>();

var app = builder.Build();

app.MapDefaultEndpoints();
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
