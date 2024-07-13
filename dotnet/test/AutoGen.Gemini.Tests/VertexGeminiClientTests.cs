// Copyright (c) Microsoft Corporation. All rights reserved.
// GeminiVertexClientTests.cs

using AutoGen.Tests;
using FluentAssertions;
using Google.Cloud.AIPlatform.V1;
using Google.Protobuf;
using static Google.Cloud.AIPlatform.V1.Candidate.Types;
namespace AutoGen.Gemini.Tests;

public class VertexGeminiClientTests
{
    [ApiKeyFact("GCP_VERTEX_PROJECT_ID")]
    public async Task ItGenerateContentAsync()
    {
        var location = "us-central1";
        var project = Environment.GetEnvironmentVariable("GCP_VERTEX_PROJECT_ID");
        var client = new VertexGeminiClient(location);
        var model = "gemini-1.5-flash-001";

        var text = "Hello";
        var request = new GenerateContentRequest
        {
            Model = $"projects/{project}/locations/{location}/publishers/google/models/{model}",
            Contents =
            {
                new Content
                {
                    Role = "user",
                    Parts =
                    {
                        new Part
                        {
                            Text = text,
                        }
                    }
                }
            }
        };
        var completion = await client.GenerateContentAsync(request);

        completion.Should().NotBeNull();
        completion.Candidates.Count.Should().BeGreaterThan(0);
        completion.Candidates[0].Content.Parts[0].Text.Should().NotBeNullOrEmpty();
    }

    [ApiKeyFact("GCP_VERTEX_PROJECT_ID")]
    public async Task ItGenerateContentWithImageAsync()
    {
        var location = "us-central1";
        var project = Environment.GetEnvironmentVariable("GCP_VERTEX_PROJECT_ID");
        var client = new VertexGeminiClient(location);
        var model = "gemini-1.5-flash-001";

        var text = "what's in the image";
        var imagePath = Path.Combine("testData", "images", "square.png");
        var image = File.ReadAllBytes(imagePath);
        var request = new GenerateContentRequest
        {
            Model = $"projects/{project}/locations/{location}/publishers/google/models/{model}",
            Contents =
            {
                new Content
                {
                    Role = "user",
                    Parts =
                    {
                        new Part
                        {
                            Text = text,
                        },
                        new Part
                        {
                            InlineData = new ()
                            {
                                MimeType = "image/png",
                                Data = ByteString.CopyFrom(image),
                            },
                        }
                    }
                }
            }
        };

        var completion = await client.GenerateContentAsync(request);
        completion.Should().NotBeNull();
        completion.Candidates.Count.Should().BeGreaterThan(0);
        completion.Candidates[0].Content.Parts[0].Text.Should().NotBeNullOrEmpty();
    }

    [ApiKeyFact("GCP_VERTEX_PROJECT_ID")]
    public async Task ItStreamingGenerateContentTestAsync()
    {
        var location = "us-central1";
        var project = Environment.GetEnvironmentVariable("GCP_VERTEX_PROJECT_ID");
        var client = new VertexGeminiClient(location);
        var model = "gemini-1.5-flash-001";

        var text = "Hello, write a long tedious joke";
        var request = new GenerateContentRequest
        {
            Model = $"projects/{project}/locations/{location}/publishers/google/models/{model}",
            Contents =
            {
                new Content
                {
                    Role = "user",
                    Parts =
                    {
                        new Part
                        {
                            Text = text,
                        }
                    }
                }
            }
        };

        var response = client.GenerateContentStreamAsync(request);
        var chunks = new List<GenerateContentResponse>();
        GenerateContentResponse? final = null;
        await foreach (var item in response)
        {
            item.Candidates.Count.Should().BeGreaterThan(0);
            final = item;
            chunks.Add(final);
        }

        chunks.Should().NotBeEmpty();
        final.Should().NotBeNull();
        final!.UsageMetadata.CandidatesTokenCount.Should().BeGreaterThan(0);
        final!.Candidates[0].FinishReason.Should().Be(FinishReason.Stop);
    }
}
