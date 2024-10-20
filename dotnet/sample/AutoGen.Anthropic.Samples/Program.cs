// Copyright (c) 2023 - 2024, Owners of https://github.com/autogenhub
// SPDX-License-Identifier: Apache-2.0
// Contributions to this project, i.e., https://github.com/autogenhub/autogen, 
// are licensed under the Apache License, Version 2.0 (Apache-2.0).
// Portions derived from  https://github.com/microsoft/autogen under the MIT License.
// SPDX-License-Identifier: MIT
// Copyright (c) Microsoft Corporation. All rights reserved.
// Program.cs

namespace AutoGen.Anthropic.Samples;

internal static class Program
{
    public static async Task Main(string[] args)
    {
        await Anthropic_Agent_With_Prompt_Caching.RunAsync();
    }
}
