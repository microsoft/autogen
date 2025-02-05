// Copyright (c) Microsoft Corporation. All rights reserved.
// AddSubscriptionResponseSurrogate.cs

using Microsoft.AutoGen.Protobuf;

namespace Microsoft.AutoGen.RuntimeGateway.Grpc.Orleans.Surrogates;

[GenerateSerializer]
public struct AddSubscriptionResponseSurrogate
{
    [Id(0)]
    public string RequestId;
    [Id(1)]
    public bool Success;
    [Id(2)]
    public string Error;
}

[RegisterConverter]
public sealed class AddSubscriptionResponseSurrogateConverter :
    IConverter<AddSubscriptionResponse, AddSubscriptionResponseSurrogate>
{
    public AddSubscriptionResponse ConvertFromSurrogate(
        in AddSubscriptionResponseSurrogate surrogate) =>
        new AddSubscriptionResponse { };

    public AddSubscriptionResponseSurrogate ConvertToSurrogate(
        in AddSubscriptionResponse value) =>
        new AddSubscriptionResponseSurrogate { };
}

