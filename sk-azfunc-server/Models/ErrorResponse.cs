using System.Text.Json.Serialization;
using Microsoft.Azure.WebJobs.Extensions.OpenApi.Core.Attributes;

namespace Models;

internal class ErrorResponse
{
    [JsonPropertyName("message")]
    [OpenApiProperty(Description = "The error message.")]
    public string Message { get; set; } = string.Empty;
}
