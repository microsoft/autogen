// Copyright (c) Microsoft Corporation. All rights reserved.
// AgentType.cs

namespace Microsoft.AutoGen.Contracts.Python;

public struct AgentType
{
    public required string Name;

    public static explicit operator AgentType(Type type) => new AgentType { Name = type.Name };

    public static implicit operator AgentType(string type) => new AgentType { Name = type };
    public static implicit operator string(AgentType type) => type.Name;
}

