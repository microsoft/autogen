// Copyright (c) Microsoft Corporation. All rights reserved.
// IGeminiClient.cs

using System.Collections.Generic;
using System.Threading;
using System.Threading.Tasks;
using Google.Cloud.AIPlatform.V1;

namespace AutoGen.Gemini;

public interface IGeminiClient
{
    Task<GenerateContentResponse> GenerateContentAsync(GenerateContentRequest request, CancellationToken cancellationToken = default);
    IAsyncEnumerable<GenerateContentResponse> GenerateContentStreamAsync(GenerateContentRequest request);
}
