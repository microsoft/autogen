using System.ComponentModel.DataAnnotations;

namespace Microsoft.AI.DevTeam;
public class OpenAIOptions
{
    [Required]
    public string ServiceType { get; set; }
    [Required]
    public string ServiceId { get; set; }
    [Required]
    public string DeploymentOrModelId { get; set; }
    [Required]
    public string EmbeddingDeploymentOrModelId { get; set; }
    [Required]
    public string Endpoint { get; set; }
    [Required]
    public string ApiKey { get; set; }
}
