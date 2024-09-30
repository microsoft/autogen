using HelloAgents.Agents;
using Microsoft.AutoGen.Agents.Client;
using Microsoft.AutoGen.Agents.Extensions.SemanticKernel;

var builder = WebApplication.CreateBuilder(args);

builder.AddServiceDefaults();

builder.ConfigureSemanticKernel();

builder.AddAgentWorker(builder.Configuration["AGENT_HOST"]!)
    .AddAgent<HelloAgent>(nameof(HelloAgent));

var app = builder.Build();

app.MapDefaultEndpoints();

app.Run();