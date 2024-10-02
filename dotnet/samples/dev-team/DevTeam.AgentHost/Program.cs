using Microsoft.AutoGen.Agents.Runtime;
var builder = WebApplication.CreateBuilder(args);

builder.AddServiceDefaults();
builder.AddAgentService();

var app = builder.Build();

app.MapDefaultEndpoints();
app.MapAgentService();

app.Run();
