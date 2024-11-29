// Copyright (c) Microsoft Corporation. All rights reserved.
// Program.cs

using DevTeam.Agents;
using Microsoft.AutoGen.Core;

var builder = WebApplication.CreateBuilder(args);

builder.AddServiceDefaults();

// TODO: Configure MS.AI.Ext in the app side
//builder.ConfigureSemanticKernel();

builder.AddAgentWorker(builder.Configuration["AGENT_HOST"]!)
    .AddAgent<Dev>(nameof(Dev))
    .AddAgent<ProductManager>(nameof(ProductManager))
    .AddAgent<DeveloperLead>(nameof(DeveloperLead));

var app = builder.Build();

app.MapDefaultEndpoints();

app.Run();
