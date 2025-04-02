// Copyright (c) Microsoft Corporation. All rights reserved.
// AnySurrogate.cs

using Google.Protobuf;
using Google.Protobuf.WellKnownTypes;

namespace Microsoft.AutoGen.RuntimeGateway.Grpc.Orleans.Surrogates;

[GenerateSerializer]
[Alias("Microsoft.AutoGen.RuntimeGateway.Grpc.Orleans.Surrogates.AnySurrogate")]
public struct AnySurrogate
{
    [Id(0)]
    public string TypeUrl;
    [Id(1)]
    public byte[] Value;
}

[RegisterConverter]
public sealed class AnySurrogateConverter : IConverter<Any, AnySurrogate>
{
    public Any ConvertFromSurrogate(in AnySurrogate surrogate) =>
        new()
        {
            TypeUrl = surrogate.TypeUrl,
            Value = ByteString.CopyFrom(surrogate.Value)
        };

    public AnySurrogate ConvertToSurrogate(in Any value) =>
        new()
        {
            TypeUrl = value.TypeUrl,
            Value = value.Value.ToByteArray()
        };
}
