// Copyright (c) 2023 - 2024, Owners of https://github.com/autogenhub
// SPDX-License-Identifier: Apache-2.0
// Contributions to this project, i.e., https://github.com/autogenhub/autogen, 
// are licensed under the Apache License, Version 2.0 (Apache-2.0).
// Portions derived from  https://github.com/microsoft/autogen under the MIT License.
// SPDX-License-Identifier: MIT
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
}
