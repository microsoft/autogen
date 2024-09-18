using Microsoft.AutoGen.Agents.Worker;

var builder = WebApplication.CreateBuilder(args);

builder.AddServiceDefaults();
builder.AddAgentService();

var app = builder.Build();

app.MapAgentService();
app.UseExceptionHandler();
app.MapDefaultEndpoints();

app.Run();
