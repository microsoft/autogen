// Copyright (c) Microsoft Corporation. All rights reserved.
// ParseExtensions.cs

namespace DevTeam;

public static class ParseExtensions
{
    public static long TryParseLong(this Dictionary<string, string> data, string key)
    {
        ArgumentNullException.ThrowIfNull(data);

        if (data.TryGetValue(key, out string? value) && !string.IsNullOrEmpty(value) && long.TryParse(value, out var result))
        {
            return result;
        }
        return default;
    }
}
