// Copyright (c) Microsoft Corporation. All rights reserved.
// MessageExtension.cs

using System.Text;

namespace AutoGen.DotnetInteractive.Extension;

public static class MessageExtension
{
    public static string ExtractCodeBlock(
        this ICanGetTextContent message,
        string codeBlockPrefix,
        string codeBlockSuffix)
    {
        var codeBlock = new StringBuilder();
        var content = message.GetContent() ?? string.Empty;
        var codeBlockStartIndex = content.IndexOf(codeBlockPrefix);
        if (codeBlockStartIndex == -1)
        {
            return string.Empty;
        }

        var codeBlockEndIndex = content.IndexOf(codeBlockSuffix, codeBlockStartIndex + codeBlockPrefix.Length);
        if (codeBlockEndIndex == -1)
        {
            return string.Empty;
        }

        codeBlock.Append(content, codeBlockStartIndex + codeBlockPrefix.Length, codeBlockEndIndex - codeBlockStartIndex - codeBlockPrefix.Length);
        return codeBlock.ToString();
    }
}
