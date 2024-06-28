using Microsoft.AI.Agents.Worker;

var builder = WebApplication.CreateBuilder(args);
builder.AddServiceDefaults();
builder.Services.AddProblemDetails();
builder.Services.AddGrpc();
builder.Logging.SetMinimumLevel(LogLevel.Information);

builder.AddAgentService();

var app = builder.Build();

app.MapAgentService();
app.UseExceptionHandler();
app.MapDefaultEndpoints();

app.Run();
