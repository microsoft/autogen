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
