// Copyright (c) Microsoft Corporation. All rights reserved.
// OllamaFact.cs

using AutoGen.Tests;

namespace Autogen.Ollama.Tests;

public class OllamaFact : EnvironmentSpecificFactAttribute
{
    private readonly string[] _envVariableNames;
    public OllamaFact(params string[] envVariableNames) : base($"{envVariableNames} is not found in env")
    {
        _envVariableNames = envVariableNames;
    }

    /// <inheritdoc />
    protected override bool IsEnvironmentSupported()
    {
        return _envVariableNames.All(Environment.GetEnvironmentVariables().Contains);
    }
}
