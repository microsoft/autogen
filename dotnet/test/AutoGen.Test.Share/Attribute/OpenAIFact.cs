// Copyright (c) 2023 - 2024, Owners of https://github.com/autogen-ai
// SPDX-License-Identifier: Apache-2.0
// Contributions to this project, i.e., https://github.com/autogen-ai/autogen, 
// are licensed under the Apache License, Version 2.0 (Apache-2.0).
// Portions derived from  https://github.com/microsoft/autogen under the MIT License.
// SPDX-License-Identifier: MIT
// Copyright (c) Microsoft Corporation. All rights reserved.
// OpenAIFact.cs

namespace AutoGen.Tests;

/// <summary>
/// A fact for tests requiring OPENAI_API_KEY env.
/// </summary>
public sealed class ApiKeyFactAttribute : EnvironmentSpecificFactAttribute
{
    private readonly string[] _envVariableNames;
    public ApiKeyFactAttribute(params string[] envVariableNames) : base($"{envVariableNames} is not found in env")
    {
        _envVariableNames = envVariableNames;
    }

    /// <inheritdoc />
    protected override bool IsEnvironmentSupported()
    {
        return _envVariableNames.All(Environment.GetEnvironmentVariables().Contains);
    }
}
