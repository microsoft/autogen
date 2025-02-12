// Copyright (c) Microsoft Corporation. All rights reserved.
// AgentExtensions.cs

using System.Reflection;
using Google.Protobuf;
using Microsoft.AutoGen.Contracts;
using Microsoft.AutoGen.Core.Grpc;

namespace Microsoft.AutoGen.Core;

internal static partial class AgentExtensions
{
    private static readonly Type ProtobufIMessage = typeof(IMessage<>);
    private static bool IsProtobufType(this Type type)
    {
        // TODO: Support the non-generic IMessage as well
        Type specializedIMessageType = ProtobufIMessage.MakeGenericType(type);

        // type T needs to derive from IMessage<T>
        return specializedIMessageType.IsAssignableFrom(type);
    }

    public static void RegisterHandledMessageTypes(this IHostableAgent agent, IProtoSerializationRegistry registry)
    {
        Type agentRuntimeType = agent.GetType();

        MethodInfo[] messageHandlers = agentRuntimeType.GetHandlers();

        foreach (MethodInfo handler in messageHandlers)
        {
            Type messageType = handler.GetParameters().First().ParameterType;
            if (messageType.IsProtobufType() && registry.GetSerializer(messageType) == null)
            {
                registry.RegisterSerializer(messageType);
            }
        }
    }
}
