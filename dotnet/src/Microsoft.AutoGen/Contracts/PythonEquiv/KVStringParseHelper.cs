// Copyright (c) Microsoft Corporation. All rights reserved.
// KVStringParseHelper.cs

using System.Text.RegularExpressions;

namespace Microsoft.AutoGen.Contracts.Python;

public static class KVStringParseHelper
{
    private const string KVPairPattern = @"^(?<key>\w+)/(?<value>\w+)$";
    private static readonly Regex KVPairRegex = new Regex(KVPairPattern, RegexOptions.Compiled);

    public static (string, string) ToKVPair(this string kvString, string keyName, string valueName)
    {
        var match = KVPairRegex.Match(kvString);
        if (match.Success)
        {
            return (match.Groups["key"].Value, match.Groups["value"].Value);
        }

        throw new FormatException($"Invalid key-value pair format: {kvString}; expecting \"{{{keyName}}}/{{{valueName}}}\"");
    }
}

