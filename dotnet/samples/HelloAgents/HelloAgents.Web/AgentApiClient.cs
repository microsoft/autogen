namespace HelloAgents.Web;

public class AgentAPIClient(HttpClient httpClient)
{
    public async Task<AgentOutputRecord[]> GetAgentResultAsync(int maxItems = 10, CancellationToken cancellationToken = default)
    {
        List<AgentOutputRecord>? forecasts = null;

        await foreach (var forecast in httpClient.GetFromJsonAsAsyncEnumerable<AgentOutputRecord>("/agents", cancellationToken))
        {
            if (forecasts?.Count >= maxItems)
            {
                break;
            }
            if (forecast is not null)
            {
                forecasts ??= [];
                forecasts.Add(forecast);
            }
        }

        return forecasts?.ToArray() ?? [];
    }
}

public record AgentOutputRecord(DateTime Date, string Content, string? Summary)
{
    public string DisplayDate => Date.ToString("d");
    public string DisplayContent => Content;
    public string DisplaySummary => Summary ?? "No summary";
}
