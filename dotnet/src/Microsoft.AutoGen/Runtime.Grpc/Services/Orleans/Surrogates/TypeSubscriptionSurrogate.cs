// Copyright (c) Microsoft Corporation. All rights reserved.
// TypeSubscriptionSurrogate.cs

using Microsoft.AutoGen.Contracts;

namespace Microsoft.AutoGen.Runtime.Grpc.Orleans.Surrogates;

[GenerateSerializer]
public struct TypeSubscriptionSurrogate
{
    [Id(0)]
    public string TopicType;
    [Id(1)]
    public string AgentType;
}

[RegisterConverter]
public sealed class TypeSubscriptionSurrogateConverter :
    IConverter<TypeSubscription, TypeSubscriptionSurrogate>
{
    public TypeSubscription ConvertFromSurrogate(
        in TypeSubscriptionSurrogate surrogate) =>
        new TypeSubscription
        {
            TopicType = surrogate.TopicType,
            AgentType = surrogate.AgentType
        };

    public TypeSubscriptionSurrogate ConvertToSurrogate(
        in TypeSubscription value) =>
        new TypeSubscriptionSurrogate
        {
            TopicType = value.TopicType,
            AgentType = value.AgentType
        };
}
