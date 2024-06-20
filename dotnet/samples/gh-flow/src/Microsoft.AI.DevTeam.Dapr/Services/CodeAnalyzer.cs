using System.Text.Json;
using Microsoft.Extensions.Options;

namespace Microsoft.AI.DevTeam.Dapr;

public interface IAnalyzeCode
{
    Task<IEnumerable<CodeAnalysisResult>> Analyze(string content);
}
public class CodeAnalyzer : IAnalyzeCode
{
    private readonly ServiceOptions _serviceOptions;
    private readonly HttpClient _httpClient;
    private readonly ILogger<CodeAnalyzer> _logger;

    public CodeAnalyzer(IOptions<ServiceOptions> serviceOptions, HttpClient httpClient, ILogger<CodeAnalyzer> logger)
    {
        ArgumentNullException.ThrowIfNull(serviceOptions);
        ArgumentNullException.ThrowIfNull(httpClient);
        ArgumentNullException.ThrowIfNull(logger);

        _serviceOptions = serviceOptions.Value;
        _httpClient = httpClient;
        _logger = logger;
        _httpClient.BaseAddress = _serviceOptions.IngesterUrl;

    }
    public async Task<IEnumerable<CodeAnalysisResult>> Analyze(string content)
    {
        try
        {
            var request = new CodeAnalysisRequest { Content = content };
            var response = await _httpClient.PostAsJsonAsync("api/AnalyzeCode", request);
            var stringResult = await response.Content.ReadAsStringAsync();
            var result = JsonSerializer.Deserialize<IEnumerable<CodeAnalysisResult>>(stringResult);
            return result ?? [];
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error analyzing code");
            return [];
        }
    }
}

public class CodeAnalysisRequest
{
    public required string Content { get; set; }
}

public class CodeAnalysisResult
{
    public required string Meaning { get; set; }
    public required string CodeBlock { get; set; }
}
