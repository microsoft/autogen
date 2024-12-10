// Copyright (c) Microsoft Corporation. All rights reserved.
// MessageExtensions.cs

using Google.Protobuf;
using Google.Protobuf.WellKnownTypes;

namespace Microsoft.AutoGen.Abstractions;

public static class MessageExtensions
{
    private const string PROTO_DATA_CONTENT_TYPE = "application/x-protobuf";
    public static CloudEvent ToCloudEvent<T>(this T message, string source) where T : IMessage
    {
        return new CloudEvent
        {
            ProtoData = Any.Pack(message),
            Type = message.Descriptor.FullName,
            Source = source,
            Id = Guid.NewGuid().ToString(),
            SpecVersion = "1.0",
            Attributes = { { "datacontenttype", new CloudEvent.Types.CloudEventAttributeValue { CeString = PROTO_DATA_CONTENT_TYPE } } }
        };
    }
    public static T FromCloudEvent<T>(this CloudEvent cloudEvent) where T : IMessage, new()
    {
        return cloudEvent.ProtoData.Unpack<T>();
    }
    public static AgentState ToAgentState<T>(this T state, AgentId agentId, string eTag) where T : IMessage
    {
        return new AgentState
        {
            ProtoData = Any.Pack(state),
            AgentId = agentId,
            ETag = eTag
        };
    }

    public static T FromAgentState<T>(this AgentState state) where T : IMessage, new()
    {
        if (state.HasTextData == true)
        {
            if (typeof(T) == typeof(AgentState))
            {
                return (T)(IMessage)state;
            }
        }
        return state.ProtoData.Unpack<T>();
    }
}
