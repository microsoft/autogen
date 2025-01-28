// Copyright (c) Microsoft Corporation. All rights reserved.
// ImageMessageTests.cs

using System;
using System.IO;
using System.Threading.Tasks;
using FluentAssertions;
using Xunit;

namespace AutoGen.Tests;

public class ImageMessageTests
{
    [Fact]
    public async Task ItCreateFromLocalImage()
    {
        var image = Path.Combine("testData", "images", "background.png");
        var binary = File.ReadAllBytes(image);
        var base64 = Convert.ToBase64String(binary);
        var imageMessage = new ImageMessage(Role.User, BinaryData.FromBytes(binary, "image/png"));

        imageMessage.MimeType.Should().Be("image/png");
        imageMessage.BuildDataUri().Should().Be($"data:image/png;base64,{base64}");
    }

    [Fact]
    public async Task ItCreateFromUrl()
    {
        var image = Path.Combine("testData", "images", "background.png");
        var fullPath = Path.GetFullPath(image);
        var localUrl = new Uri(fullPath).AbsoluteUri;
        var imageMessage = new ImageMessage(Role.User, localUrl);

        imageMessage.Url.Should().Be(localUrl);
        imageMessage.MimeType.Should().Be("image/png");
        imageMessage.Data.Should().BeNull();
    }

    [Fact]
    public async Task ItCreateFromBase64Url()
    {
        var image = Path.Combine("testData", "images", "background.png");
        var binary = File.ReadAllBytes(image);
        var base64 = Convert.ToBase64String(binary);

        var base64Url = $"data:image/png;base64,{base64}";
        var imageMessage = new ImageMessage(Role.User, base64Url);

        imageMessage.BuildDataUri().Should().Be(base64Url);
        imageMessage.MimeType.Should().Be("image/png");
    }
}
