// Copyright (c) Microsoft Corporation. All rights reserved.
// AddSubscriptionRequestSurrogate.cs

using Microsoft.AutoGen.Contracts;

namespace Microsoft.AutoGen.Runtime.Grpc.Orleans.Surrogates;

[GenerateSerializer]
public struct AddSubscriptionRequestSurrogate
{
    [Id(0)]
    public string RequestId;
    [Id(1)]
    public Subscription Subscription;
}

[RegisterConverter]
public sealed class AddSubscriptionRequestSurrogateConverter :
    IConverter<AddSubscriptionRequest, AddSubscriptionRequestSurrogate>
{
    public AddSubscriptionRequest ConvertFromSurrogate(
        in AddSubscriptionRequestSurrogate surrogate)
    {
        var request = new AddSubscriptionRequest()
        {
            RequestId = surrogate.RequestId,
            Subscription = surrogate.Subscription
        };
        return request;
    }

    public AddSubscriptionRequestSurrogate ConvertToSurrogate(
        in AddSubscriptionRequest value) =>
        new AddSubscriptionRequestSurrogate
        {
            RequestId = value.RequestId,
            Subscription = value.Subscription
        };
}
