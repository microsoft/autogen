// Copyright (c) Microsoft Corporation. All rights reserved.
// GoogleGeminiClientTests.cs

using AutoGen.Tests;
using FluentAssertions;
using Google.Cloud.AIPlatform.V1;
using Google.Protobuf;
using Xunit;
using static Google.Cloud.AIPlatform.V1.Candidate.Types;

namespace AutoGen.Gemini.Tests;

[Trait("Category", "UnitV1")]
public class GoogleGeminiClientTests
{
    [ApiKeyFact("GOOGLE_GEMINI_API_KEY")]
    public async Task ItGenerateContentAsync()
    {
        var apiKey = Environment.GetEnvironmentVariable("GOOGLE_GEMINI_API_KEY") ?? throw new InvalidOperationException("GOOGLE_GEMINI_API_KEY is not set");
        var client = new GoogleGeminiClient(apiKey);
        var model = "gemini-1.5-flash-001";

        var text = "Write a long, tedious story";
        var request = new GenerateContentRequest
        {
            Model = model,
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

    [ApiKeyFact("GOOGLE_GEMINI_API_KEY")]
    public async Task ItGenerateContentWithImageAsync()
    {
        var apiKey = Environment.GetEnvironmentVariable("GOOGLE_GEMINI_API_KEY") ?? throw new InvalidOperationException("GOOGLE_GEMINI_API_KEY is not set");
        var client = new GoogleGeminiClient(apiKey);
        var model = "gemini-1.5-flash-001";

        var text = "what's in the image";
        var imagePath = Path.Combine("testData", "images", "background.png");
        var image = File.ReadAllBytes(imagePath);
        var request = new GenerateContentRequest
        {
            Model = model,
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

    [ApiKeyFact("GOOGLE_GEMINI_API_KEY")]
    public async Task ItStreamingGenerateContentTestAsync()
    {
        var apiKey = Environment.GetEnvironmentVariable("GOOGLE_GEMINI_API_KEY") ?? throw new InvalidOperationException("GOOGLE_GEMINI_API_KEY is not set");
        var client = new GoogleGeminiClient(apiKey);
        var model = "gemini-1.5-flash-001";

        var text = "Tell me a long tedious joke";
        var request = new GenerateContentRequest
        {
            Model = model,
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
