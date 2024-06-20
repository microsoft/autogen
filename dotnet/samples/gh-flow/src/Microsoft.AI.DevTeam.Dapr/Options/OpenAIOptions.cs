using System.ComponentModel.DataAnnotations;

namespace Microsoft.AI.DevTeam.Dapr;
public class OpenAIOptions
{
    [Required]
    public required string ServiceType { get; set; }
    [Required]
    public required string ServiceId { get; set; }
    [Required]
    public required string DeploymentOrModelId { get; set; }
    [Required]
    public required string EmbeddingDeploymentOrModelId { get; set; }
    [Required]
    public required string Endpoint { get; set; }
    [Required]
    public required string ApiKey { get; set; }
}
