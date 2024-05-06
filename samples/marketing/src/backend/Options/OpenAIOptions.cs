using System.ComponentModel.DataAnnotations;

namespace Marketing.Options;

public class OpenAIOptions
{
    // Embeddings
    [Required]
    public string EmbeddingsEndpoint { get; set; }
    [Required]
    public string EmbeddingsApiKey { get; set; }
    [Required]
    public string EmbeddingsDeploymentOrModelId { get; set; }

    // Chat
    [Required]
    public string ChatEndpoint { get; set; }
    [Required]
    public string ChatApiKey { get; set; }
    [Required]
    public string ChatDeploymentOrModelId { get; set; }

    // TextToImage
    [Required]
    public string ImageEndpoint { get; set; }
    [Required]
    public string ImageApiKey { get; set; }
    // When using OpenAI, this is not required.
    public string ImageDeploymentOrModelId { get; set; }
}