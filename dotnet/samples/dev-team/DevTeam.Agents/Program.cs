// Copyright (c) Microsoft Corporation. All rights reserved.
// Program.cs

using DevTeam.Agents;
using Microsoft.AutoGen.Agents;
using Microsoft.AutoGen.Extensions.SemanticKernel;

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
