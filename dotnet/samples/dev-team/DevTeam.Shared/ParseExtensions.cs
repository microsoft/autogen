// Copyright (c) Microsoft. All rights reserved.

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