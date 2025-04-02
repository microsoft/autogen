// Copyright (c) Microsoft Corporation. All rights reserved.
// AgentIdSurrogate.cs

// Copyright (c) Microsoft Corporation. All rights reserved.
// AgentIdSurrogate.cs
using Microsoft.AutoGen.Protobuf;

namespace Microsoft.AutoGen.RuntimeGateway.Grpc.Orleans.Surrogates;

[GenerateSerializer]
public struct AgentIdSurrogate
{
    [Id(0)]
    public string Key;
    [Id(1)]
    public string Type;
}

[RegisterConverter]
public sealed class AgentIdSurrogateConverter :
    IConverter<AgentId, AgentIdSurrogate>
{
    public AgentId ConvertFromSurrogate(
        in AgentIdSurrogate surrogate) =>
        new AgentId
        {
            Key = surrogate.Key,
            Type = surrogate.Type
        };

    public AgentIdSurrogate ConvertToSurrogate(
        in AgentId value) =>
        new AgentIdSurrogate
        {
            Key = value.Key,
            Type = value.Type
        };
}
