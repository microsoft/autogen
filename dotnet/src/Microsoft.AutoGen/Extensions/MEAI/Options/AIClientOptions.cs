// Copyright (c) Microsoft Corporation. All rights reserved.
// AIClientOptions.cs

using System.ComponentModel.DataAnnotations;

namespace Microsoft.Extensions.Hosting;

public class AIClientOptions
{
    // Model Classname
    [Required]
    public required string ModelType { get; set; }
    // Embeddings
    [Required]
    public required string EmbeddingsEndpoint { get; set; }
    [Required]
    public required string EmbeddingsApiKey { get; set; }
    [Required]
    public required string EmbeddingsDeploymentOrModelId { get; set; }

    // Chat
    [Required]
    public required string ChatEndpoint { get; set; }
    [Required]
    public required string ChatApiKey { get; set; }
    [Required]
    public required string ChatDeploymentOrModelId { get; set; }

    // TextToImage
    [Required]
    public required string ImageEndpoint { get; set; }
    [Required]
    public required string ImageApiKey { get; set; }
    // When using OpenAI, this is not required.
    public required string ImageDeploymentOrModelId { get; set; }
}
