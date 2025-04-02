// Copyright (c) Microsoft Corporation. All rights reserved.
// CloudEventSurrogate.cs
using Google.Protobuf;
using Google.Protobuf.WellKnownTypes;
using Microsoft.AutoGen.Contracts;

namespace Microsoft.AutoGen.RuntimeGateway.Grpc.Orleans.Surrogates;

// TODO: Add the rest of the properties
[GenerateSerializer]
public struct CloudEventSurrogate
{
    [Id(0)]
    public string Id;
    [Id(1)]
    public string TextData;
    [Id(2)]
    public ByteString BinaryData;
    [Id(3)]
    public Any ProtoData;
}

[RegisterConverter]
public sealed class CloudEventSurrogateConverter :
    IConverter<CloudEvent, CloudEventSurrogate>
{
    public CloudEvent ConvertFromSurrogate(
        in CloudEventSurrogate surrogate) =>
        new CloudEvent
        {
            TextData = surrogate.TextData,
            BinaryData = surrogate.BinaryData,
            Id = surrogate.Id
        };

    public CloudEventSurrogate ConvertToSurrogate(
        in CloudEvent value) =>
        new CloudEventSurrogate
        {
            TextData = value.TextData,
            BinaryData = value.BinaryData,
            Id = value.Id,
            ProtoData = value.ProtoData
        };
}
