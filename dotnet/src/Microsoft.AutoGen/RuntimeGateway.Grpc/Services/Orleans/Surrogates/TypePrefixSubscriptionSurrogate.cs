// Copyright (c) Microsoft Corporation. All rights reserved.
// TypePrefixSubscriptionSurrogate.cs

using Microsoft.AutoGen.Protobuf;

namespace Microsoft.AutoGen.RuntimeGateway.Grpc.Orleans.Surrogates;

[GenerateSerializer]
public struct TypePrefixSubscriptionSurrogate
{
    [Id(0)]
    public string TopicTypePrefix;
    [Id(1)]
    public string AgentType;
}

[RegisterConverter]
public sealed class TypePrefixSubscriptionConverter :
    IConverter<TypePrefixSubscription, TypePrefixSubscriptionSurrogate>
{
    public TypePrefixSubscription ConvertFromSurrogate(
        in TypePrefixSubscriptionSurrogate surrogate) =>
        new TypePrefixSubscription
        {
            TopicTypePrefix = surrogate.TopicTypePrefix,
            AgentType = surrogate.AgentType
        };

    public TypePrefixSubscriptionSurrogate ConvertToSurrogate(
        in TypePrefixSubscription value) =>
        new TypePrefixSubscriptionSurrogate
        {
            TopicTypePrefix = value.TopicTypePrefix,
            AgentType = value.AgentType
        };
}
