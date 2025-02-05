// Copyright (c) Microsoft Corporation. All rights reserved.
// RpcRequestSurrogate.cs

using Google.Protobuf.Collections;
using Microsoft.AutoGen.Contracts;

namespace Microsoft.AutoGen.Runtime.Grpc.Orleans.Surrogates;

[GenerateSerializer]
public struct RpcRequestSurrogate
{
    [Id(0)]
    public string RequestId;
    [Id(1)]
    public AgentId Source;
    [Id(2)]
    public AgentId Target;
    [Id(3)]
    public string Method;
    [Id(4)]
    public Payload Payload;
    [Id(5)]
    public MapField<string, string> Metadata;
}

[RegisterConverter]
public sealed class RpcRequestSurrogateConverter :
    IConverter<RpcRequest, RpcRequestSurrogate>
{
    public RpcRequest ConvertFromSurrogate(
        in RpcRequestSurrogate surrogate) =>
    new RpcRequest
    {
        RequestId = surrogate.RequestId,
        Source = surrogate.Source,
        Target = surrogate.Target,
        Method = surrogate.Method,
        Payload = surrogate.Payload,
        Metadata = { surrogate.Metadata }
    };

    public RpcRequestSurrogate ConvertToSurrogate(
        in RpcRequest value) =>
        new RpcRequestSurrogate
        {
            RequestId = value.RequestId,
            Source = value.Source,
            Target = value.Target,
            Method = value.Method,
            Payload = value.Payload,
            Metadata = value.Metadata
        };
}

