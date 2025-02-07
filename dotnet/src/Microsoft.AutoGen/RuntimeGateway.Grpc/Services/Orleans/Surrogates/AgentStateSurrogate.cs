// Copyright (c) Microsoft Corporation. All rights reserved.
// AgentStateSurrogate.cs
using Google.Protobuf;
using Microsoft.AutoGen.RuntimeGateway.Grpc.Abstractions;

namespace Microsoft.AutoGen.RuntimeGateway.Grpc.Orleans.Surrogates;

[GenerateSerializer]
public struct AgentStateSurrogate
{
    [Id(0)]
    public string Id;
    [Id(1)]
    public string? TextData;
    [Id(2)]
    public ByteString? BinaryData;
    [Id(3)]
    public Protobuf.AgentId AgentId;
    [Id(4)]
    public string Etag;
    [Id(5)]
    public Google.Protobuf.WellKnownTypes.Any? ProtoData;
    [Id(6)]
    public object? Data;
}

[RegisterConverter]
public sealed class AgentStateSurrogateConverter :
    IConverter<AgentState, AgentStateSurrogate>
{
    public AgentState ConvertFromSurrogate(
        in AgentStateSurrogate surrogate)
    {
        var agentState = new AgentState
        {
            AgentId = surrogate.AgentId,
            BinaryData = surrogate.BinaryData,
            TextData = surrogate.TextData,
            ETag = surrogate.Etag,
            ProtoData = surrogate.ProtoData,
            Data = surrogate.Data
        };
        //agentState.ProtoData = surrogate.ProtoData;
        return agentState;
    }

    public AgentStateSurrogate ConvertToSurrogate(
        in AgentState value) =>
        new AgentStateSurrogate
        {
            AgentId = value.AgentId,
            BinaryData = value.BinaryData,
            TextData = value.TextData,
            Etag = value.ETag,
            ProtoData = value.ProtoData,
            Data = value.Data
        };
}

