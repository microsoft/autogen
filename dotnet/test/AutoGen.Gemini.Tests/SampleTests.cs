// Copyright (c) Microsoft Corporation. All rights reserved.
// SampleTests.cs

using AutoGen.Gemini.Sample;
using AutoGen.Tests;
using Xunit;

namespace AutoGen.Gemini.Tests;

[Trait("Category", "UnitV1")]
public class SampleTests
{
    [ApiKeyFact("GCP_VERTEX_PROJECT_ID")]
    public async Task TestChatWithVertexGeminiAsync()
    {
        await Chat_With_Vertex_Gemini.RunAsync();
    }

    [ApiKeyFact("GCP_VERTEX_PROJECT_ID")]
    public async Task TestFunctionCallWithGeminiAsync()
    {
        await Function_Call_With_Gemini.RunAsync();
    }

    [ApiKeyFact("GCP_VERTEX_PROJECT_ID")]
    public async Task TestImageChatWithVertexGeminiAsync()
    {
        await Image_Chat_With_Vertex_Gemini.RunAsync();
    }
}
