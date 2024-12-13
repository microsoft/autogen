// Copyright (c) Microsoft Corporation. All rights reserved.
// AgentId.cs

namespace Microsoft.AutoGen.Contracts;

public partial class AgentId
{
    public AgentId(string type, string key)
    {
        Type = type;
        Key = key;
    }
}
