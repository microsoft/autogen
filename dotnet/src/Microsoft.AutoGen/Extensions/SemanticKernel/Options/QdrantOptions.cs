// Copyright (c) Microsoft Corporation. All rights reserved.
// QdrantOptions.cs

using System.ComponentModel.DataAnnotations;

namespace Microsoft.AutoGen.Extensions.SemanticKernel;
public class QdrantOptions
{
    [Required]
    public required string Endpoint { get; set; }
    [Required]
    public required int VectorSize { get; set; }
    public string ApiKey { get; set; } = "";
}
