using Microsoft.AutoGen.Agents.Worker.Client;
using DevTeam;
using DevTeam.Agents;

var builder = WebApplication.CreateBuilder(args);

builder.AddServiceDefaults();

builder.ConfigureSemanticKernel();

builder.AddAgentWorker(builder.Configuration["AGENT_HOST"]!)
    .AddAgent<Dev>(nameof(Dev))
    .AddAgent<ProductManager>(nameof(ProductManager))
    .AddAgent<DeveloperLead>(nameof(DeveloperLead));

var app = builder.Build();

app.MapDefaultEndpoints();

app.Run();