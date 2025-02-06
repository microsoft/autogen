// Copyright (c) Microsoft Corporation. All rights reserved.
// ProtobufConversionExtensions.cs

using Microsoft.AutoGen.Contracts;
using Microsoft.AutoGen.Protobuf;

namespace Microsoft.AutoGen.Core.Grpc;

public static class ProtobufConversionExtensions
{
    // Convert an ISubscrptionDefinition to a Protobuf Subscription
    public static Subscription? ToProtobuf(this ISubscriptionDefinition subscriptionDefinition)
    {
        // Check if is a TypeSubscription
        if (subscriptionDefinition is Contracts.TypeSubscription typeSubscription)
        {
            return new Subscription
            {
                Id = typeSubscription.Id,
                TypeSubscription = new Protobuf.TypeSubscription
                {
                    TopicType = typeSubscription.TopicType,
                    AgentType = typeSubscription.AgentType
                }
            };
        }

        // Check if is a TypePrefixSubscription
        if (subscriptionDefinition is Contracts.TypePrefixSubscription typePrefixSubscription)
        {
            return new Subscription
            {
                Id = typePrefixSubscription.Id,
                TypePrefixSubscription = new Protobuf.TypePrefixSubscription
                {
                    TopicTypePrefix = typePrefixSubscription.TopicTypePrefix,
                    AgentType = typePrefixSubscription.AgentType
                }
            };
        }

        return null;
    }

    // Convert AgentId from Protobuf to AgentId
    public static Contracts.AgentId FromProtobuf(this Protobuf.AgentId agentId)
    {
        return new Contracts.AgentId(agentId.Type, agentId.Key);
    }

    // Convert AgentId from AgentId to Protobuf
    public static Protobuf.AgentId ToProtobuf(this Contracts.AgentId agentId)
    {
        return new Protobuf.AgentId
        {
            Type = agentId.Type,
            Key = agentId.Key
        };
    }
}
