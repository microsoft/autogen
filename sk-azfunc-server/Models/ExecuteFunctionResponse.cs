using System.Text.Json.Serialization;
using Microsoft.Azure.WebJobs.Extensions.OpenApi.Core.Attributes;

namespace Models;

internal class ExecuteFunctionResponse
{
    [JsonPropertyName("response")]
    [OpenApiProperty(Description = "The response from the AI.")]
    public string? Response { get; set; }
}
