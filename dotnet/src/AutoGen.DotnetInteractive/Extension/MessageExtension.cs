// Copyright (c) Microsoft Corporation. All rights reserved.
// MessageExtension.cs

using System.Text.RegularExpressions;

namespace AutoGen.DotnetInteractive.Extension;

public static class MessageExtension
{
    /// <summary>
    /// Extract a single code block from a message. If the message contains multiple code blocks, only the first one will be returned.
    /// </summary>
    /// <param name="message"></param>
    /// <param name="codeBlockPrefix">code block prefix, e.g. ```csharp</param>
    /// <param name="codeBlockSuffix">code block suffix, e.g. ```</param>
    /// <returns></returns>
    public static string? ExtractCodeBlock(
        this IMessage message,
        string codeBlockPrefix,
        string codeBlockSuffix)
    {
        foreach (var codeBlock in message.ExtractCodeBlocks(codeBlockPrefix, codeBlockSuffix))
        {
            return codeBlock;
        }

        return null;
    }

    /// <summary>
    /// Extract all code blocks from a message.
    /// </summary>
    /// <param name="message"></param>
    /// <param name="codeBlockPrefix">code block prefix, e.g. ```csharp</param>
    /// <param name="codeBlockSuffix">code block suffix, e.g. ```</param>
    /// <returns></returns>
    public static IEnumerable<string> ExtractCodeBlocks(
        this IMessage message,
        string codeBlockPrefix,
        string codeBlockSuffix)
    {
        var content = message.GetContent() ?? string.Empty;
        if (string.IsNullOrWhiteSpace(content))
        {
            yield break;
        }

        foreach (Match match in Regex.Matches(content, $@"{codeBlockPrefix}([\s\S]*?){codeBlockSuffix}"))
        {
            yield return match.Groups[1].Value.Trim();
        }
    }
}
