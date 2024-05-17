// Copyright (c) Microsoft Corporation. All rights reserved.
// ITextEmbeddingService.cs

using System.Threading;
using System.Threading.Tasks;

namespace Autogen.Ollama;

public interface ITextEmbeddingService
{
    public Task<TextEmbeddingsResponse> GenerateAsync(TextEmbeddingsRequest request, CancellationToken cancellationToken);
}
