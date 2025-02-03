// Copyright (c) Microsoft Corporation. All rights reserved.
// MessageExtensionTests.cs

using AutoGen.Core;
using AutoGen.DotnetInteractive.Extension;
using FluentAssertions;
using Xunit;

namespace AutoGen.DotnetInteractive.Tests;

[Trait("Category", "UnitV1")]
public class MessageExtensionTests
{
    [Fact]
    public void ExtractCodeBlock_WithSingleCodeBlock_ShouldReturnCodeBlock()
    {
        // Arrange
        var message = new TextMessage(Role.Assistant, "```csharp\nConsole.WriteLine(\"Hello, World!\");\n```");
        var codeBlockPrefix = "```csharp";
        var codeBlockSuffix = "```";

        // Act
        var codeBlock = message.ExtractCodeBlock(codeBlockPrefix, codeBlockSuffix);

        codeBlock.Should().BeEquivalentTo("Console.WriteLine(\"Hello, World!\");");
    }

    [Fact]
    public void ExtractCodeBlock_WithMultipleCodeBlocks_ShouldReturnFirstCodeBlock()
    {
        // Arrange
        var message = new TextMessage(Role.Assistant, "```csharp\nConsole.WriteLine(\"Hello, World!\");\n```\n```csharp\nConsole.WriteLine(\"Hello, World!\");\n```");
        var codeBlockPrefix = "```csharp";
        var codeBlockSuffix = "```";

        // Act
        var codeBlock = message.ExtractCodeBlock(codeBlockPrefix, codeBlockSuffix);

        codeBlock.Should().BeEquivalentTo("Console.WriteLine(\"Hello, World!\");");
    }

    [Fact]
    public void ExtractCodeBlock_WithNoCodeBlock_ShouldReturnNull()
    {
        // Arrange
        var message = new TextMessage(Role.Assistant, "Hello, World!");
        var codeBlockPrefix = "```csharp";
        var codeBlockSuffix = "```";

        // Act
        var codeBlock = message.ExtractCodeBlock(codeBlockPrefix, codeBlockSuffix);

        codeBlock.Should().BeNull();
    }

    [Fact]
    public void ExtractCodeBlocks_WithMultipleCodeBlocks_ShouldReturnAllCodeBlocks()
    {
        // Arrange
        var message = new TextMessage(Role.Assistant, "```csharp\nConsole.WriteLine(\"Hello, World!\");\n```\n```csharp\nConsole.WriteLine(\"Hello, World!\");\n```");
        var codeBlockPrefix = "```csharp";
        var codeBlockSuffix = "```";

        // Act
        var codeBlocks = message.ExtractCodeBlocks(codeBlockPrefix, codeBlockSuffix);

        codeBlocks.Should().HaveCount(2);
        codeBlocks.ElementAt(0).Should().BeEquivalentTo("Console.WriteLine(\"Hello, World!\");");
        codeBlocks.ElementAt(1).Should().BeEquivalentTo("Console.WriteLine(\"Hello, World!\");");
    }

    [Fact]
    public void ExtractCodeBlocks_WithNoCodeBlock_ShouldReturnEmpty()
    {
        // Arrange
        var message = new TextMessage(Role.Assistant, "Hello, World!");
        var codeBlockPrefix = "```csharp";
        var codeBlockSuffix = "```";

        // Act
        var codeBlocks = message.ExtractCodeBlocks(codeBlockPrefix, codeBlockSuffix);

        codeBlocks.Should().BeEmpty();
    }
}
