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
                TypeSubscription = surrogate.TypeSubscription
            };
        }
        else
        {
            return new Subscription
            {
                TypePrefixSubscription = surrogate.TypePrefixSubscription
            };
        }
    }

    public SubscriptionSurrogate ConvertToSurrogate(
        in Subscription value)
    {
        return new SubscriptionSurrogate
        {
            TypeSubscription = value.TypeSubscription,
            TypePrefixSubscription = value.TypePrefixSubscription
        };
    }
}
