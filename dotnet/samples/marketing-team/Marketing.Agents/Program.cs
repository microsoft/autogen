// Copyright (c) Microsoft Corporation. All rights reserved.
// Program.cs

using Marketing.Agents;
using Marketing.Shared;
using Microsoft.AutoGen.Agents;

var builder = WebApplication.CreateBuilder(args);

builder.AddServiceDefaults();

builder.ConfigureSemanticKernel();

builder.AddAgentWorker(builder.Configuration["AGENT_HOST"]!)
    .AddAgent<Writer>("writer")
    .AddAgent<GraphicDesigner>("graphic-designer")
    .AddAgent<Auditor>("auditor")
    .AddAgent<CommunityManager>("community-manager");

var app = builder.Build();

app.MapDefaultEndpoints();

app.Run();
