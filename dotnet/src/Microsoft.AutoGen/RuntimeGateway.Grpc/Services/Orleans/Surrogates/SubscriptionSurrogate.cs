// Copyright (c) Microsoft Corporation. All rights reserved.
// SubscriptionSurrogate.cs

using Microsoft.AutoGen.Contracts;

namespace Microsoft.AutoGen.Runtime.Grpc.Orleans.Surrogates;

[GenerateSerializer]
public struct SubscriptionSurrogate
{
    [Id(0)]
    public TypeSubscription? TypeSubscription;
    [Id(1)]
    public TypePrefixSubscription? TypePrefixSubscription;
    [Id(2)]
    public string Id;
}

[RegisterConverter]
public sealed class SubscriptionSurrogateConverter :
    IConverter<Subscription, SubscriptionSurrogate>
{
    public Subscription ConvertFromSurrogate(
        in SubscriptionSurrogate surrogate)
    {
        if (surrogate.TypeSubscription is not null)
        {
            return new Subscription
            {
                Id = surrogate.Id,
                TypeSubscription = surrogate.TypeSubscription
            };
        }
        else
        {
            return new Subscription
            {
                Id = surrogate.Id,
                TypePrefixSubscription = surrogate.TypePrefixSubscription
            };
        }
    }

    public SubscriptionSurrogate ConvertToSurrogate(
        in Subscription value)
    {
        return new SubscriptionSurrogate
        {
            Id = value.Id,
            TypeSubscription = value.TypeSubscription,
            TypePrefixSubscription = value.TypePrefixSubscription
        };
    }
}
