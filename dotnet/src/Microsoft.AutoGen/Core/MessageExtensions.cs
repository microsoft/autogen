// Copyright (c) Microsoft Corporation. All rights reserved.
// MessageExtensions.cs

using Google.Protobuf;
using Google.Protobuf.WellKnownTypes;
using Microsoft.AutoGen.Contracts;

namespace Microsoft.AutoGen.Core;

/// <summary>
/// Provides extension methods for converting messages to and from various formats.
/// </summary>
public static class MessageExtensions
{
    private const string PROTO_DATA_CONTENT_TYPE = "application/x-protobuf";

    /// <summary>
    /// Converts a message to a CloudEvent.
    /// </summary>
    /// <typeparam name="T">The type of the message.</typeparam>
    /// <param name="message">The message to convert.</param>
    /// <param name="key">The key of the event, maps to the Topic Type</param>
    /// <param name="topic">The topic of the event, </param>
    /// <returns>A CloudEvent representing the message.</returns>
    public static CloudEvent ToCloudEvent<T>(this T message, string key, string topic) where T : IMessage
    {
        return new CloudEvent
        {
            ProtoData = Any.Pack(message),
            Type = message.Descriptor.FullName,
            Source = topic,
            Id = Guid.NewGuid().ToString(),
            Attributes = {
                {
                    "datacontenttype", new CloudEvent.Types.CloudEventAttributeValue { CeString = PROTO_DATA_CONTENT_TYPE }
                },
                {
                    "subject", new CloudEvent.Types.CloudEventAttributeValue { CeString = key }
                }
            }
        };
    }

    /// <summary>
    /// Converts a CloudEvent back to a message.
    /// </summary>
    /// <typeparam name="T">The type of the message.</typeparam>
    /// <param name="cloudEvent">The CloudEvent to convert.</param>
    /// <returns>The message represented by the CloudEvent.</returns>
    public static T FromCloudEvent<T>(this CloudEvent cloudEvent) where T : IMessage, new()
    {
        return cloudEvent.ProtoData.Unpack<T>();
    }

    /// <summary>
    public static string GetSubject(this CloudEvent cloudEvent)
    {
        if (cloudEvent.Attributes.TryGetValue("subject", out var value))
        {
            return value.CeString;
        }
        else
        {
            return string.Empty;
        }
    }

    /// <summary>
    /// Converts a state to an AgentState.
    /// </summary>
    /// <typeparam name="T">The type of the state.</typeparam>
    /// <param name="state">The state to convert.</param>
    /// <param name="agentId">The ID of the agent.</param>
    /// <param name="eTag">The ETag of the state.</param>
    /// <returns>An AgentState representing the state.</returns>
    public static AgentState ToAgentState<T>(this T state, AgentId agentId, string eTag) where T : IMessage
    {
        return new AgentState
        {
            ProtoData = Any.Pack(state),
            AgentId = agentId,
            ETag = eTag
        };
    }

    /// <summary>
    /// Converts an AgentState back to a state.
    /// </summary>
    /// <typeparam name="T">The type of the state.</typeparam>
    /// <param name="state">The AgentState to convert.</param>
    /// <returns>The state represented by the AgentState.</returns>
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
