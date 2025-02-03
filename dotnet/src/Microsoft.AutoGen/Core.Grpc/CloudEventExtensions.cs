// Copyright (c) Microsoft Corporation. All rights reserved.
// CloudEventExtensions.cs

using Microsoft.AutoGen.Contracts;

namespace Microsoft.AutoGen.Core.Grpc;

internal static class CloudEventExtensions
{
    // Convert an ISubscrptionDefinition to a Protobuf Subscription
    internal static CloudEvent CreateCloudEvent(Google.Protobuf.WellKnownTypes.Any payload, TopicId topic, string dataType, AgentId sender, string messageId)
    {
        return new CloudEvent
        {
            ProtoData = payload,
            Type = topic.Type,
            Source = topic.Source,
            Id = messageId,
            Attributes = {
                {
                    Constants.DATA_CONTENT_TYPE_ATTR, new CloudEvent.Types.CloudEventAttributeValue { CeString = Constants.DATA_CONTENT_TYPE_PROTOBUF_VALUE }
                },
                {
                    Constants.DATA_SCHEMA_ATTR, new CloudEvent.Types.CloudEventAttributeValue { CeString = dataType }
                },
                {
                    Constants.AGENT_SENDER_TYPE_ATTR, new CloudEvent.Types.CloudEventAttributeValue { CeString = sender.Type }
                },
                {
                    Constants.AGENT_SENDER_KEY_ATTR, new CloudEvent.Types.CloudEventAttributeValue { CeString = sender.Key }
                },
                {
                    Constants.MESSAGE_KIND_ATTR, new CloudEvent.Types.CloudEventAttributeValue { CeString = Constants.MESSAGE_KIND_VALUE_PUBLISH }
                }
            }
        };

    }
}
