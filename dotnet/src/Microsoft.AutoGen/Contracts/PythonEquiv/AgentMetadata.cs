// Copyright (c) Microsoft Corporation. All rights reserved.
// PythonInterfaces.cs

namespace Microsoft.AutoGen.Contracts.Python;

public struct AgentMetadata(string type, string key, string description)
{
    public string Type { get; set; } = type;
    public string Key { get; set; } = key;
    public string Description { get; set; } = description;
}

