// Copyright (c) Microsoft Corporation. All rights reserved.
// RemoveSubscriptionResponse.cs

using Microsoft.AutoGen.Contracts;

namespace Microsoft.AutoGen.Runtime.Grpc.Orleans.Surrogates;

[GenerateSerializer]
public struct RemoveSubscriptionResponseSurrogate
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
    IConverter<RemoveSubscriptionResponse, RemoveSubscriptionResponseSurrogate>
{
    public RemoveSubscriptionResponse ConvertFromSurrogate(
        in RemoveSubscriptionResponseSurrogate surrogate) =>
        new RemoveSubscriptionResponse
        {
            Success = surrogate.Success,
            Error = surrogate.Error
        };

    public RemoveSubscriptionResponseSurrogate ConvertToSurrogate(
        in RemoveSubscriptionResponse value) =>
        new RemoveSubscriptionResponseSurrogate
        {
            Success = value.Success,
            Error = value.Error
        };
}

