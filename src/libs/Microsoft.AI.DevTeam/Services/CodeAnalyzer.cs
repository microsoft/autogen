using System.Text;
using System.Text.Json;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Options;

namespace Microsoft.AI.DevTeam;

public interface IAnalyzeCode 
{
    Task<IEnumerable<CodeAnalysis>> Analyze(string content);
}
public class CodeAnalyzer : IAnalyzeCode
{
    private readonly ServiceOptions _serviceOptions;
    private readonly HttpClient _httpClient;
    private readonly ILogger<CodeAnalyzer> _logger;

    public CodeAnalyzer(IOptions<ServiceOptions> serviceOptions, HttpClient httpClient, ILogger<CodeAnalyzer> logger)
    {
        _serviceOptions = serviceOptions.Value;
        _httpClient = httpClient;
        _logger = logger;
        _httpClient.BaseAddress = new Uri(_serviceOptions.IngesterUrl);
        
    }
    public async Task<IEnumerable<CodeAnalysis>> Analyze(string content)
    {
        try
        {
             var request = new CodeAnalysisRequest { Content = content };
            var body = new StringContent(JsonSerializer.Serialize(request), Encoding.UTF8, "application/json");
            var response = await _httpClient.PostAsync("api/AnalyzeCode", body);
            var stringResult = await response.Content.ReadAsStringAsync();
            var result = JsonSerializer.Deserialize<IEnumerable<CodeAnalysis>>(stringResult);
            return result;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error analyzing code");
            return Enumerable.Empty<CodeAnalysis>();
        }
    }
}

public class CodeAnalysisRequest
{
    public string Content { get; set; }
}

public class CodeAnalysis
{
    public string Meaning { get; set; }
    public string CodeBlock { get; set; }
}
