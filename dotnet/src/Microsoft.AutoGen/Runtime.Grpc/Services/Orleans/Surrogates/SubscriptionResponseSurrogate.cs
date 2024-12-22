// Copyright (c) Microsoft Corporation. All rights reserved.
// SubscriptionResponseSurrogate.cs

using Microsoft.AutoGen.Contracts;

namespace Microsoft.AutoGen.Runtime.Grpc.Orleans.Surrogates;

[GenerateSerializer]
public struct SubscriptionResponseSurrogate
{
    [Id(0)]
    public string RequestId;
    [Id(1)]
    public bool Success;
    [Id(2)]
    public string Error;
}

[RegisterConverter]
public sealed class SubscriptionResponseSurrogateConverter :
    IConverter<SubscriptionResponse, SubscriptionResponseSurrogate>
{
    public SubscriptionResponse ConvertFromSurrogate(
        in SubscriptionResponseSurrogate surrogate) =>
        new SubscriptionResponse
        {
            RequestId = surrogate.RequestId,
            Success = surrogate.Success,
            Error = surrogate.Error
        };

    public SubscriptionResponseSurrogate ConvertToSurrogate(
        in SubscriptionResponse value) =>
        new SubscriptionResponseSurrogate
        {
            RequestId = value.RequestId,
            Success = value.Success,
            Error = value.Error
        };
}

