// Copyright (c) Microsoft Corporation. All rights reserved.
// Program.cs

using Azure.Identity;
using DevTeam.Backend;
using DevTeam.Options;
using Microsoft.AI.DevTeam;
using Microsoft.AutoGen.Agents;
using Microsoft.AutoGen.Extensions.SemanticKernel;
using Microsoft.Extensions.Azure;
using Microsoft.Extensions.Options;
using Octokit.Webhooks;
using Octokit.Webhooks.AspNetCore;

var builder = WebApplication.CreateBuilder(args);

builder.AddServiceDefaults();
builder.ConfigureSemanticKernel();

builder.Services.AddHttpClient();
builder.Services.AddControllers();
builder.Services.AddSwaggerGen();

builder.AddAgentWorker(builder.Configuration["AGENT_HOST"]!)
    .AddAgent<AzureGenie>(nameof(AzureGenie))
    //.AddAgent<Sandbox>(nameof(Sandbox))
    .AddAgent<Hubber>(nameof(Hubber));

builder.Services.AddSingleton<AgentWorker>();
builder.Services.AddSingleton<WebhookEventProcessor, GithubWebHookProcessor>();
builder.Services.AddSingleton<GithubAuthService>();
builder.Services.AddSingleton<IManageAzure, AzureService>();
builder.Services.AddSingleton<IManageGithub, GithubService>();

builder.Services.AddTransient(s =>
{
    var ghOptions = s.GetRequiredService<IOptions<GithubOptions>>();
    var logger = s.GetRequiredService<ILogger<GithubAuthService>>();
    var ghService = new GithubAuthService(ghOptions, logger);
    var client = ghService.GetGitHubClient();
    return client;
});

// TODO: Rework?
builder.Services.AddOptions<GithubOptions>()
    .Configure<IConfiguration>((settings, configuration) =>
    {
        configuration.GetSection("Github").Bind(settings);
    })
    .ValidateDataAnnotations()
    .ValidateOnStart();

builder.Services.AddAzureClients(clientBuilder =>
{
    clientBuilder.AddArmClient(default);
    clientBuilder.UseCredential(new DefaultAzureCredential());
});

var app = builder.Build();

app.MapDefaultEndpoints();
app.UseRouting()
.UseEndpoints(endpoints =>
{
    var ghOptions = app.Services.GetRequiredService<IOptions<GithubOptions>>().Value;
    endpoints.MapGitHubWebhooks(secret: ghOptions.WebhookSecret);
}); ;

app.UseSwagger();
/* app.UseSwaggerUI(c =>
{
    c.SwaggerEndpoint("/swagger/v1/swagger.json", "My API V1");
}); */

app.Run();
