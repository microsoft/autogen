// Copyright (c) Microsoft Corporation. All rights reserved.
// RpcResponseSurrogate.cs
using Google.Protobuf.Collections;
using Microsoft.AutoGen.Protobuf;

namespace Microsoft.AutoGen.RuntimeGateway.Grpc.Orleans.Surrogates;

[GenerateSerializer]
public struct RpcResponseSurrogate
{
    [Id(0)]
    public string RequestId;
    [Id(1)]
    public Payload Payload;
    [Id(2)]
    public string Error;
    [Id(3)]
    public MapField<string, string> Metadata;
}

[RegisterConverter]
public sealed class RpcResponseurrogateConverter :
    IConverter<RpcResponse, RpcResponseSurrogate>
{
    public RpcResponse ConvertFromSurrogate(
        in RpcResponseSurrogate surrogate) =>
    new RpcResponse
    {
        RequestId = surrogate.RequestId,
        Payload = surrogate.Payload,
        Error = surrogate.Error,
        Metadata = { surrogate.Metadata }
    };

    public RpcResponseSurrogate ConvertToSurrogate(
        in RpcResponse value) =>
        new RpcResponseSurrogate
        {
            RequestId = value.RequestId,
            Payload = value.Payload,
            Error = value.Error,
            Metadata = value.Metadata
        };
}

