// Copyright (c) Microsoft Corporation. All rights reserved.
// SubscriptionRequestSurrogate.cs

using Microsoft.AutoGen.Contracts;

namespace Microsoft.AutoGen.Runtime.Grpc.Orleans.Surrogates;

[GenerateSerializer]
public struct SubscriptionRequestSurrogate
{
    [Id(0)]
    public string RequestId;
    [Id(1)]
    public Subscription Subscription;
}

[RegisterConverter]
public sealed class SubscriptionRequestSurrogateConverter :
    IConverter<SubscriptionRequest, SubscriptionRequestSurrogate>
{
    public SubscriptionRequest ConvertFromSurrogate(
        in SubscriptionRequestSurrogate surrogate)
    {
        var request = new SubscriptionRequest()
        {
            RequestId = surrogate.RequestId,
            Subscription = surrogate.Subscription
        };
        return request;
    }

    public SubscriptionRequestSurrogate ConvertToSurrogate(
        in SubscriptionRequest value) =>
        new SubscriptionRequestSurrogate
        {
            RequestId = value.RequestId,
            Subscription = value.Subscription
        };
}
