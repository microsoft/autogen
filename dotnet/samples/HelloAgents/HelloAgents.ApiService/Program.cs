var builder = WebApplication.CreateBuilder(args);

// Add service defaults & Aspire components.
builder.AddServiceDefaults();

// Add services to the container.
builder.Services.AddProblemDetails();

var app = builder.Build();

// Configure the HTTP request pipeline.
app.UseExceptionHandler();

var summaries = new[]
{
    "Freezing", "Bracing", "Chilly", "Cool", "Mild", "Warm", "Balmy", "Hot", "Sweltering", "Scorching"
};

app.MapGet("/agents", () =>
{
    // here is where we call an agent

    var result = Enumerable.Range(1, 5).Select(index =>
        new AgentOutputRecord
        (
            Date: DateTime.Now.AddDays(index),
            Content: $"AgentResult {DateTime.Now.AddDays(index):d}",
            Summary: summaries[DateTime.Now.AddDays(index).DayOfYear % summaries.Length]
        ))
        .ToArray();
    return result;
});

app.MapDefaultEndpoints();

app.Run();

public record AgentOutputRecord(DateTime Date, string Content, string? Summary)
{
    public string DisplayDate => Date.ToString("d");
    public string DisplayContent => Content;
    public string DisplaySummary => Summary ?? "No summary";
}
