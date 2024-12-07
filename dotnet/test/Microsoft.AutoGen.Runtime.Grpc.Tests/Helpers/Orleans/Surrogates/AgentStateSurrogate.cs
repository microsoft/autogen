// Copyright (c) Microsoft Corporation. All rights reserved.
// AgentStateSurrogate.cs

using Google.Protobuf;
using Microsoft.AutoGen.Abstractions;

namespace Microsoft.AutoGen.Runtime.Grpc.Tests.Helpers.Orleans.Surrogates;

[GenerateSerializer]
public struct AgentStateSurrogate
{
    [Id(0)]
    public string Id;
    [Id(1)]
    public string TextData;
    [Id(2)]
    public ByteString BinaryData;
    [Id(3)]
    public AgentId AgentId;
    [Id(4)]
    public string Etag;
    [Id(5)]
    public ByteString ProtoData;
}

[RegisterConverter]
public sealed class AgentStateSurrogateConverter :
    IConverter<AgentState, AgentStateSurrogate>
{
    public AgentState ConvertFromSurrogate(
        in AgentStateSurrogate surrogate) =>
        new AgentState
        {
            TextData = surrogate.TextData,
            BinaryData = surrogate.BinaryData,
            AgentId = surrogate.AgentId,
           // ProtoData = surrogate.ProtoData,
            ETag = surrogate.Etag
        };

    public AgentStateSurrogate ConvertToSurrogate(
        in AgentState value) =>
        new AgentStateSurrogate
        {
            AgentId = value.AgentId,
            BinaryData = value.BinaryData,
            TextData = value.TextData,
            Etag = value.ETag,
            //ProtoData = value.ProtoData.Value
        };
}

