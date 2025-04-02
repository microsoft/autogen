// Copyright (c) Microsoft Corporation. All rights reserved.
// TypeSubscriptionSurrogate.cs

using Microsoft.AutoGen.Protobuf;
namespace Microsoft.AutoGen.RuntimeGateway.Grpc.Orleans.Surrogates;

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
    /// <summary>
    /// Converts from the surrogate to the original type.
    /// </summary>
    /// <param name="surrogate">The surrogate to convert from.</param>
    /// <returns>The original type.</returns>
    public TypeSubscription ConvertFromSurrogate(
        in TypeSubscriptionSurrogate surrogate) =>
        new TypeSubscription
        {
            TopicType = surrogate.TopicType,
            AgentType = surrogate.AgentType
        };

    /// <summary>
    /// Converts from the original type to the surrogate.
    /// </summary>
    /// <param name="value">The original type to convert from.</param>
    /// <returns>The surrogate type.</returns>
    public TypeSubscriptionSurrogate ConvertToSurrogate(
        in TypeSubscription value) =>
        new TypeSubscriptionSurrogate
        {
            TopicType = value.TopicType,
            AgentType = value.AgentType
        };
}
